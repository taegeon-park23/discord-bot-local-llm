import discord
import os
import re
import asyncio
import datetime
import glob
import aiohttp
from src.logger import get_logger, LOG_FILE

logger = get_logger(__name__)

from src.config import (
    DISCORD_TOKEN, INPUT_CHANNEL_ID, OUTPUT_CHANNEL_ID, 
    MANAGEMENT_CHANNEL_ID, SAVE_DIR
)
from src.services.drive_handler import DriveUploader
from src.services.content_extractor import ContentExtractor
from src.services.ai_handler import AIAgent
from src.services.llm_queue import LLMQueue, LLMJob

class KnowledgeBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        super().__init__(intents=intents)
        self.extractor = ContentExtractor()
        self.ai = AIAgent()
        self.uploader = DriveUploader()
        self.queue = LLMQueue(self)
        if not os.path.exists(SAVE_DIR): os.makedirs(SAVE_DIR)

    async def on_ready(self):
        logger.info(f'Logged in as {self.user}')
        # Start LLM Queue Worker
        self.queue.start()
        await self.send_ngrok_url(MANAGEMENT_CHANNEL_ID, initial=True)

    async def get_ngrok_url(self):
        candidate_urls = ["http://ngrok_tunnel:4040/api/tunnels", "http://host.docker.internal:4040/api/tunnels"]
        logger.info("[Ngrok] URL 탐색 시작...")
        for url in candidate_urls:
            try:
                logger.info(f"[Ngrok] 접속 시도: {url}")
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=2) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get('tunnels'):
                                public_url = data['tunnels'][0]['public_url']
                                logger.info(f"[Ngrok] ✅ 성공: {public_url}")
                                return public_url
            except: pass
        return None

    async def send_ngrok_url(self, channel_id, initial=False):
        channel = self.get_channel(channel_id)
        if not channel: return
        url = await self.get_ngrok_url()
        if url:
            msg = f"🚀 **지식 저장소 & 드라이브 연동 중!**\n접속: {url}" if initial else f"🌐 **주소:**\n{url}"
            await channel.send(msg)
        elif not initial:
            await channel.send("⚠️ Ngrok 터널을 찾을 수 없습니다.")

    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.user.id: return
        
        target_emojis = ["🕵️‍♂️", "🕵️", "🕵", "🔍"]
        if str(payload.emoji) in target_emojis:
            channel = self.get_channel(payload.channel_id)
            if not channel: return
            try: message = await channel.fetch_message(payload.message_id)
            except: return

            url_match = re.search(r'(https?://\S+)', message.content)
            target_url = url_match.group(0) if url_match else (message.embeds[0].url if message.embeds else None)
            if not target_url: return

            await channel.send(f"🕵️‍♂️ **Deep Dive 시작...** (드라이브 업로드 포함 / 큐 대기 가능)")
            try:
                data = await self.extractor.extract(target_url)
                if "error" in data:
                    logger.warning(f"콘텐츠 추출 실패: {data['error']}")
                    await channel.send(f"⚠️ 추출 실패: {data['error']}")
                    return

                await self.queue.add_job(LLMJob(
                    type='deep_dive',
                    payload={'content': data['content'], 'url': target_url},
                    context=message
                ))
            except Exception as e:
                logger.error(f"Deep Dive 요청 처리 중 오류: {e}", exc_info=True)
                await channel.send(f"❌ 오류: {e}")

    async def on_message(self, message):
        if message.author == self.user: return

        if message.channel.id == MANAGEMENT_CHANNEL_ID:
            if "!url" in message.content or "주소" in message.content:
                await self.send_ngrok_url(message.channel.id)
            elif message.content.startswith("!weekly"):
                await self._handle_weekly_report(message)
            elif message.content.startswith("!ask"):
                await self._handle_ask_question(message)
            elif message.content.startswith("!log"):
                await self._handle_log_request(message)
            return

        if message.channel.id == INPUT_CHANNEL_ID:
            await self._handle_link_submission(message)

    async def _handle_weekly_report(self, message):
        logger.info("주간 리포트 요청 수신")
        await message.channel.send("📅 **주간 리포트** 생성 중...")
        report_files = []
        today = datetime.datetime.now()
        files = glob.glob(os.path.join(SAVE_DIR, "*.md"))
        
        for f in files:
            if "[DeepDive]" in f: continue
            try:
                file_date = datetime.datetime.strptime(os.path.basename(f)[:10], "%Y-%m-%d")
                if (today - file_date).days <= 7:
                    with open(f, 'r', encoding='utf-8') as rf:
                        content = rf.read()
                        if "## 📝 3줄 요약" in content:
                            summary = content.split("## 📝 3줄 요약")[1].split("##")[0].strip()
                            report_files.append(f"- **{os.path.basename(f)[11:-3]}**:\n{summary}")
            except: continue

        if not report_files:
            await message.channel.send("⚠️ 최근 7일간 데이터가 없습니다.")
            return

        context_text = "\n\n".join(report_files)
        await self.queue.add_job(LLMJob(
            type='weekly',
            payload={'context_text': context_text},
            context=message
        ))

    async def _handle_ask_question(self, message):
        query = message.content.replace("!ask", "").strip()
        if not query:
            await message.channel.send("사용법: `!ask <질문>`")
            return
        
        logger.info(f"질문 요청 수신: {query}")
        await message.add_reaction("🤔")
        files = glob.glob(os.path.join(SAVE_DIR, "*.md"))
        docs = []
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as rf:
                    content = rf.read()
                    if query in content or any(t in content for t in query.split()):
                        docs.append(f"Source: {os.path.basename(f)}\nContent: {content[:1000]}...")
            except: continue
        
        if not docs:
            await message.channel.send("⚠️ 관련 자료가 없습니다.")
            await message.remove_reaction("🤔", self.user)
            return

        await self.queue.add_job(LLMJob(
            type='ask',
            payload={'query': query, 'docs': docs},
            context=message
        ))
        await message.remove_reaction("🤔", self.user)

    async def _handle_log_request(self, message):
        """!log [--lines] 명령을 처리합니다."""
        lines_to_read = 100
        args = message.content.split()
        for arg in args:
            if arg.startswith("--"):
                try:
                    lines_to_read = int(arg[2:])
                except: pass
        
        if not os.path.exists(LOG_FILE):
            await message.channel.send("⚠️ 로그 파일이 존재하지 않습니다.")
            return

        try:
            # 마지막 N줄 읽기
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                # 효율적인 tail 구현 (deque 사용)
                from collections import deque
                lines = deque(f, maxlen=lines_to_read)
                log_content = "".join(lines)
            
            if not log_content:
                await message.channel.send("⚠️ 로그가 비어있습니다.")
                return

            # 내용이 짧으면 메시지로, 길면 파일로 전송
            if len(log_content) < 1900:
                await message.channel.send(f"📋 **최근 로그 ({len(lines)} lines):**\n```log\n{log_content}```")
            else:
                # 임시 파일 생성
                temp_log_path = os.path.join(SAVE_DIR, f"log_tail_{lines_to_read}.txt")
                with open(temp_log_path, "w", encoding="utf-8") as f:
                    f.write(log_content)
                
                await message.channel.send(
                    f"📋 **최근 로그 ({len(lines)} lines)**", 
                    file=discord.File(temp_log_path)
                )
                # 전송 후 임시 파일 삭제
                os.remove(temp_log_path)

        except Exception as e:
            logger.error(f"로그 조회 실패: {e}")
            await message.channel.send(f"❌ 로그 조회 실패: {e}")

    async def _handle_link_submission(self, message):
        url_match = re.search(r'(https?://\S+)', message.content)
        if not url_match: return
        target_url = url_match.group(0)
        
        logger.info(f"링크 수신: {target_url}")

        await message.add_reaction("👀")
        try:
            data = await self.extractor.extract(target_url)
            if "error" in data:
                logger.warning(f"링크 추출 실패: {data['error']}")
                await message.channel.send(f"⚠️ {data['error']}")
                await message.remove_reaction("👀", self.user)
                return

            clean_url = self.extractor.normalize_url(target_url)
            await self.queue.add_job(LLMJob(
                type='summary',
                payload={'content': data['content'], 'url': clean_url, 'source_type': data['type']},
                context=message
            ))
        except Exception as e:
            logger.error(f"링크 처리 중 오류: {e}", exc_info=True)
            await message.channel.send(f"Error: {e}")
            await message.remove_reaction("👀", self.user)

    async def _save_and_upload(self, data, url, source_type, message):
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        safe_title = re.sub(r'[\\/*?:"<>|]', "", data.get('title', 'Untitled'))
        filename = f"{date_str}_{safe_title}.md"
        filepath = os.path.join(SAVE_DIR, filename)
        
        summary = "\n".join([f"- {s}" for s in data.get('summary', [])]) if isinstance(data.get('summary'), list) else str(data.get('summary'))
        content = f"---\ntitle: \"{data.get('title')}\"\ndate: {date_str}\ncategory: {data.get('category')}\nurl: {url}\n---\n# {data.get('title')}\n\n## 📝 3줄 요약\n{summary}\n\n## 🔗 원본\n{url} ({source_type})"
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # Blocking I/O를 별도 스레드로 분리하여 이벤트 루프 차단 방지
        await asyncio.to_thread(self.uploader.upload, filepath, data.get('title'))

        await message.remove_reaction("👀", self.user)
        await message.add_reaction("✅")
        
        out_ch = self.get_channel(OUTPUT_CHANNEL_ID)
        if out_ch:
            embed = discord.Embed(title=data.get('title'), url=url, color=0x00ff00)
            embed.add_field(name="요약", value=summary, inline=False)
            embed.set_footer(text=f"Local LLM • Drive Uploaded • Remaining: {self.queue.qsize()}")
            await out_ch.send(embed=embed)

        # 요청 채널에 남은 작업 수 알림
        await message.channel.send(f"📉 남은 작업: {self.queue.qsize()}개")

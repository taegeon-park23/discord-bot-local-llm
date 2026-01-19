import discord
import os
import re
import asyncio
import datetime
import glob
import aiohttp

from src.config import (
    DISCORD_TOKEN, INPUT_CHANNEL_ID, OUTPUT_CHANNEL_ID, 
    MANAGEMENT_CHANNEL_ID, SAVE_DIR
)
from src.services.drive_handler import DriveUploader
from src.services.content_extractor import ContentExtractor
from src.services.ai_handler import AIAgent

class KnowledgeBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        super().__init__(intents=intents)
        self.extractor = ContentExtractor()
        self.ai = AIAgent()
        self.uploader = DriveUploader()
        if not os.path.exists(SAVE_DIR): os.makedirs(SAVE_DIR)

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        await self.send_ngrok_url(MANAGEMENT_CHANNEL_ID, initial=True)

    async def get_ngrok_url(self):
        candidate_urls = ["http://ngrok_tunnel:4040/api/tunnels", "http://host.docker.internal:4040/api/tunnels"]
        print(f"\n[Ngrok] URL 탐색 시작...")
        for url in candidate_urls:
            try:
                print(f"[Ngrok] 접속 시도: {url}")
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=2) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get('tunnels'):
                                public_url = data['tunnels'][0]['public_url']
                                print(f"[Ngrok] ✅ 성공: {public_url}")
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

            await channel.send(f"🕵️‍♂️ **Deep Dive 시작...** (드라이브 업로드 포함)")
            try:
                data = await self.extractor.extract(target_url)
                if "error" in data:
                    await channel.send(f"⚠️ 추출 실패: {data['error']}")
                    return

                deep_analysis = await asyncio.to_thread(self.ai.deep_dive, data['content'])
                if not deep_analysis:
                    await channel.send("❌ AI 분석 실패")
                    return

                date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                title_match = re.search(r'^#\s+(.+)', deep_analysis)
                title = title_match.group(1).strip() if title_match else "DeepDive"
                safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
                filename = f"{date_str}_[DeepDive]_{safe_title}.md"
                filepath = os.path.join(SAVE_DIR, filename)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"{deep_analysis}\n\n---\n**Source:** {target_url}")

                uploaded = self.uploader.upload(filepath, title)
                drive_msg = "📂 **Drive 업로드 완료**" if uploaded else "⚠️ **Drive 실패**"

                if len(deep_analysis) > 1900:
                    preview = deep_analysis[:1000] + "\n\n...(중략)..."
                    await channel.send(f"✅ **분석 완료** ({drive_msg})\n파일명: `{filename}`\n\n{preview}")
                else:
                    await channel.send(f"✅ **분석 완료** ({drive_msg})\n\n{deep_analysis}")
            except Exception as e:
                print(f"Deep Dive Error: {e}")
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
            return

        if message.channel.id == INPUT_CHANNEL_ID:
            await self._handle_link_submission(message)

    async def _handle_weekly_report(self, message):
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

        context = "\n\n".join(report_files)
        try:
            resp = await asyncio.to_thread(self.ai.client.chat.completions.create, model="local-model", messages=[
                {"role": "system", "content": "Summarize user's weekly tech learning trends in Korean. Group by topics."},
                {"role": "user", "content": f"Articles:\n{context}"}
            ], temperature=0.3)
            report = resp.choices[0].message.content
            
            filename = f"Weekly_Report_{today.strftime('%Y%m%d')}.md"
            filepath = os.path.join(SAVE_DIR, filename)
            with open(filepath, "w", encoding='utf-8') as f: f.write(report)
            
            self.uploader.upload(filepath, "Weekly Report")
            
            if len(report) > 1900:
                await message.channel.send(f"✅ **주간 리포트 완료!** (파일 및 드라이브 저장됨)")
            else:
                await message.channel.send(f"📊 **주간 트렌드**\n{report}")
        except Exception as e:
            await message.channel.send(f"❌ 생성 실패: {e}")

    async def _handle_ask_question(self, message):
        query = message.content.replace("!ask", "").strip()
        if not query:
            await message.channel.send("사용법: `!ask <질문>`")
            return
        
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

        try:
            resp = await asyncio.to_thread(self.ai.client.chat.completions.create, model="local-model", messages=[
                {"role": "system", "content": "Answer the question based strictly on the provided Context. Answer in Korean."},
                {"role": "user", "content": f"Context:\n{''.join(docs[:5])}\n\nQ: {query}"}
            ], temperature=0.1)
            await message.channel.send(f"💡 **답변:**\n{resp.choices[0].message.content}")
        except: await message.channel.send("❌ 답변 실패")
        await message.remove_reaction("🤔", self.user)

    async def _handle_link_submission(self, message):
        url_match = re.search(r'(https?://\S+)', message.content)
        if not url_match: return
        target_url = url_match.group(0)

        await message.add_reaction("👀")
        try:
            data = await self.extractor.extract(target_url)
            if "error" in data:
                await message.channel.send(f"⚠️ {data['error']}")
                await message.remove_reaction("👀", self.user)
                return

            analysis = await asyncio.to_thread(self.ai.analyze, data['content'])
            if not analysis:
                await message.channel.send("❌ 분석 실패")
                await message.remove_reaction("👀", self.user)
                return

            clean_url = self.extractor.normalize_url(target_url)
            await self._save_and_upload(analysis, clean_url, data['type'], message)
        except Exception as e:
            print(f"Link Error: {e}")
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

        self.uploader.upload(filepath, data.get('title'))

        await message.remove_reaction("👀", self.user)
        await message.add_reaction("✅")
        
        out_ch = self.get_channel(OUTPUT_CHANNEL_ID)
        if out_ch:
            embed = discord.Embed(title=data.get('title'), url=url, color=0x00ff00)
            embed.add_field(name="요약", value=summary, inline=False)
            embed.set_footer(text="Local LLM • Drive Uploaded")
            await out_ch.send(embed=embed)

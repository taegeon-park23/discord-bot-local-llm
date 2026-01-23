import asyncio
import os
import re
import datetime
from dataclasses import dataclass
from typing import Any, Callable, Optional
import discord
from src.logger import get_logger

logger = get_logger(__name__)

@dataclass
class LLMJob:
    type: str  # 'summary', 'deep_dive', 'ask', 'weekly'
    payload: Any
    context: Optional[discord.Message] = None
    on_complete: Optional[Callable] = None

class LLMQueue:
    def __init__(self, bot):
        from src.config import LLM_CONCURRENCY, OUTPUT_CHANNEL_ID
        self.bot = bot
        self.queue = asyncio.Queue()
        self.is_running = True
        self.concurrency = LLM_CONCURRENCY
        self.output_channel_id = OUTPUT_CHANNEL_ID

    def qsize(self):
        return self.queue.qsize()

    def start(self):
        """설정된 동시성만큼 워커 스레드를 시작합니다."""
        logger.info(f"[Queue] 워커 시작 (Concurrency: {self.concurrency})")
        for i in range(self.concurrency):
            self.bot.loop.create_task(self.worker(i + 1))

    async def add_job(self, job: LLMJob):
        await self.queue.put(job)
        if job.context:
            try:
                await job.context.add_reaction("⏳")
            except: pass
        logger.info(f"[Queue] 작업 추가됨: {job.type}. 대기열 크기: {self.queue.qsize()}")

    async def worker(self, worker_id):
        logger.info(f"[Queue] Worker-{worker_id} 시작.")
        while self.is_running:
            job = await self.queue.get()
            logger.info(f"[Queue][Worker-{worker_id}] 작업 처리 시작: {job.type}")
            
            try:
                if job.context:
                    try:
                        await job.context.remove_reaction("⏳", self.bot.user)
                        await job.context.add_reaction("🔄")
                    except: pass

                if job.type == 'summary':
                    await self._process_summary(job)
                elif job.type == 'deep_dive':
                    await self._process_deep_dive(job)
                elif job.type == 'ask':
                    await self._process_ask(job)
                elif job.type == 'weekly':
                    await self._process_weekly(job)
                
                logger.info(f"[Queue][Worker-{worker_id}] 작업 완료: {job.type}")
                if job.context:
                    try:
                        await job.context.remove_reaction("🔄", self.bot.user)
                        await job.context.add_reaction("✅")
                    except: pass

            except Exception as e:
                logger.error(f"[Queue][Worker-{worker_id}] 작업 처리 중 오류 발생 ({job.type})", exc_info=True)
                if job.context:
                    try:
                        await job.context.remove_reaction("🔄", self.bot.user)
                        await job.context.add_reaction("❌")
                        await job.context.channel.send(f"❌ 작업 중 오류 발생: {e}")
                    except: pass
            finally:
                self.queue.task_done()

    async def _process_summary(self, job):
        # payload: {'content': str, 'url': str, 'source_type': str}
        payload = job.payload
        logger.info(f"[_process_summary] LLM 분석 요청 시작 (길이: {len(payload['content'])})")
        analysis = await asyncio.to_thread(self.bot.ai.analyze, payload['content'])
        logger.info("[_process_summary] LLM 분석 완료")
        
        if analysis:
            await self.bot._save_and_upload(analysis, payload['url'], payload['source_type'], job.context)
        else:
            raise Exception("AI 분석 결과가 비어있습니다.")

    async def _process_deep_dive(self, job):
        # payload: {'content': str, 'url': str}
        import re, datetime, os
        from src.config import SAVE_DIR
        
        payload = job.payload
        logger.info(f"[_process_deep_dive] LLM 심층 분석 요청 시작 (길이: {len(payload['content'])})")
        deep_analysis = await asyncio.to_thread(self.bot.ai.deep_dive, payload['content'])
        logger.info("[_process_deep_dive] LLM 심층 분석 완료")

        if not deep_analysis:
            raise Exception("AI 심층 분석 결과가 비어있습니다.")

        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        title_match = re.search(r'^#\s+(.+)', deep_analysis)
        title = title_match.group(1).strip() if title_match else "DeepDive"
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        
        # Determine Topic for Folder (Analyze title/content implicitly or just use default)
        # Deep Dive typically doesn't have explicit tags in payload, so we use title keywords
        from src.services.tag_manager import TagManager
        tm = TagManager()
        topic = tm.get_primary_topic(title.split())
        
        save_path = os.path.join(SAVE_DIR, topic)
        if not os.path.exists(save_path): os.makedirs(save_path)
        
        filename = f"{date_str}_[DeepDive]_{safe_title}.md"
        filepath = os.path.join(save_path, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"{deep_analysis}\n\n---\n**Source:** {payload['url']}")
        logger.info(f"[_process_deep_dive] 파일 저장됨: {filename}")

        # Blocking I/O
        uploaded = await asyncio.to_thread(self.bot.uploader.upload, filepath, title)
        drive_msg = "📂 **Drive 업로드 완료**" if uploaded else "⚠️ **Drive 실패**"

        # 결과 채널로 전송 (서머리 채널)
        out_channel = self.bot.get_channel(self.output_channel_id)
        if out_channel:
            if len(deep_analysis) > 1900:
                preview = deep_analysis[:1000] + "\n\n...(중략)..."
                await out_channel.send(f"✅ **[Deep Dive] 분석 완료** ({drive_msg})\n파일명: `{filename}`\n원본: {payload['url']}\n\n{preview}")
            else:
                await out_channel.send(f"✅ **[Deep Dive] 분석 완료** ({drive_msg})\n원본: {payload['url']}\n\n{deep_analysis}")

        # 요청 채널(링크 공유 채널)에는 완료 알림 및 큐 상태 전송
        await job.context.channel.send(f"✅ **Deep Dive 완료** (서머리 채널 확인)\n📉 남은 작업: {self.queue.qsize()}개")

    async def _process_ask(self, job):
        # payload: {'query': str, 'docs': list}
        payload = job.payload
        logger.info(f"[_process_ask] 질문 처리 시작: {payload['query']}")
        try:
            system_prompt = "Answer the question based strictly on the provided Context. Answer in Korean."
            resp_content = await asyncio.to_thread(self.bot.ai.chat, messages=[
                {"role": "user", "content": f"{system_prompt}\n\n---Context:\n{''.join(payload['docs'][:5])}\n\nQ: {payload['query']}"}
            ], temperature=0.1)
            
            if not resp_content:
                raise Exception("AI 답변 생성 실패 (Empty response)")
                
            logger.info("[_process_ask] 답변 생성 완료")
            await job.context.channel.send(f"💡 **답변:**\n{resp_content}")
        except Exception as e:
            raise Exception(f"AI 답변 생성 실패: {e}")

    async def _process_weekly(self, job):
        # payload: {'context_text': str}
        import datetime, os
        from src.config import SAVE_DIR

        payload = job.payload
        logger.info("[_process_weekly] 주간 리포트 생성 시작")
        try:
            system_prompt = "Summarize user's weekly tech learning trends in Korean. Group by topics."
            report = await asyncio.to_thread(self.bot.ai.chat, messages=[
                {"role": "user", "content": f"{system_prompt}\n\n---Articles:\n{payload['context_text']}"}
            ], temperature=0.3)

            if not report:
                raise Exception("AI 리포트 생성 실패 (Empty response)")
            logger.info("[_process_weekly] 리포트 생성 완료")
            
            today = datetime.datetime.now()
            filename = f"Weekly_Report_{today.strftime('%Y%m%d')}.md"
            filepath = os.path.join(SAVE_DIR, filename)
            with open(filepath, "w", encoding='utf-8') as f: f.write(report)
            
            await asyncio.to_thread(self.bot.uploader.upload, filepath, "Weekly Report")
            
            if len(report) > 1900:
                await job.context.channel.send(f"✅ **주간 리포트 완료!** (파일 및 드라이브 저장됨)")
            else:
                await job.context.channel.send(f"📊 **주간 트렌드**\n{report}")
        except Exception as e:
            raise Exception(f"주간 리포트 생성 실패: {e}")

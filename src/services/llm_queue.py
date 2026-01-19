import asyncio
import os
import re
import datetime
from dataclasses import dataclass
from typing import Any, Callable, Optional
import discord

@dataclass
class LLMJob:
    type: str  # 'summary', 'deep_dive', 'ask', 'weekly'
    payload: Any
    context: Optional[discord.Message] = None
    on_complete: Optional[Callable] = None

class LLMQueue:
    def __init__(self, bot):
        self.bot = bot
        self.queue = asyncio.Queue()
        self.is_running = True

    async def add_job(self, job: LLMJob):
        await self.queue.put(job)
        if job.context:
            try:
                await job.context.add_reaction("⏳")
            except: pass
        print(f"[Queue] Job added: {job.type}. Queue size: {self.queue.qsize()}")

    async def worker(self):
        print("[Queue] Worker started.")
        while self.is_running:
            job = await self.queue.get()
            print(f"[Queue] Processing job: {job.type}")
            
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
                
                if job.context:
                    try:
                        await job.context.remove_reaction("🔄", self.bot.user)
                        await job.context.add_reaction("✅")
                    except: pass

            except Exception as e:
                print(f"[Queue] Error processing job {job.type}: {e}")
                if job.context:
                    try:
                        await job.context.remove_reaction("🔄", self.bot.user)
                        await job.context.add_reaction("❌")
                        await job.context.channel.send(f"❌ 작업 중 오류 발생: {e}")
                    except: pass
            finally:
                self.queue.task_done()
                print(f"[Queue] Job finished: {job.type}")

    async def _process_summary(self, job):
        # payload: {'content': str, 'url': str, 'source_type': str}
        payload = job.payload
        analysis = await asyncio.to_thread(self.bot.ai.analyze, payload['content'])
        if analysis:
            await self.bot._save_and_upload(analysis, payload['url'], payload['source_type'], job.context)
        else:
            raise Exception("AI 분석 실패")

    async def _process_deep_dive(self, job):
        # payload: {'content': str, 'url': str}
        import re, datetime, os
        from src.config import SAVE_DIR
        
        payload = job.payload
        deep_analysis = await asyncio.to_thread(self.bot.ai.deep_dive, payload['content'])
        if not deep_analysis:
            raise Exception("AI 분석 실패")

        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        title_match = re.search(r'^#\s+(.+)', deep_analysis)
        title = title_match.group(1).strip() if title_match else "DeepDive"
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        filename = f"{date_str}_[DeepDive]_{safe_title}.md"
        filepath = os.path.join(SAVE_DIR, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"{deep_analysis}\n\n---\n**Source:** {payload['url']}")

        uploaded = self.bot.uploader.upload(filepath, title)
        drive_msg = "📂 **Drive 업로드 완료**" if uploaded else "⚠️ **Drive 실패**"

        channel = job.context.channel
        if len(deep_analysis) > 1900:
            preview = deep_analysis[:1000] + "\n\n...(중략)..."
            await channel.send(f"✅ **분석 완료** ({drive_msg})\n파일명: `{filename}`\n\n{preview}")
        else:
            await channel.send(f"✅ **분석 완료** ({drive_msg})\n\n{deep_analysis}")

    async def _process_ask(self, job):
        # payload: {'query': str, 'docs': list}
        payload = job.payload
        try:
            resp = await asyncio.to_thread(self.bot.ai.client.chat.completions.create, model="local-model", messages=[
                {"role": "system", "content": "Answer the question based strictly on the provided Context. Answer in Korean."},
                {"role": "user", "content": f"Context:\n{''.join(payload['docs'][:5])}\n\nQ: {payload['query']}"}
            ], temperature=0.1)
            await job.context.channel.send(f"💡 **답변:**\n{resp.choices[0].message.content}")
        except:
            raise Exception("AI 답변 생성 실패")

    async def _process_weekly(self, job):
        # payload: {'context_text': str}
        import datetime, os
        from src.config import SAVE_DIR

        payload = job.payload
        try:
            resp = await asyncio.to_thread(self.bot.ai.client.chat.completions.create, model="local-model", messages=[
                {"role": "system", "content": "Summarize user's weekly tech learning trends in Korean. Group by topics."},
                {"role": "user", "content": f"Articles:\n{payload['context_text']}"}
            ], temperature=0.3)
            report = resp.choices[0].message.content
            
            today = datetime.datetime.now()
            filename = f"Weekly_Report_{today.strftime('%Y%m%d')}.md"
            filepath = os.path.join(SAVE_DIR, filename)
            with open(filepath, "w", encoding='utf-8') as f: f.write(report)
            
            self.bot.uploader.upload(filepath, "Weekly Report")
            
            if len(report) > 1900:
                await job.context.channel.send(f"✅ **주간 리포트 완료!** (파일 및 드라이브 저장됨)")
            else:
                await job.context.channel.send(f"📊 **주간 트렌드**\n{report}")
        except Exception as e:
            raise Exception(f"주간 리포트 생성 실패: {e}")

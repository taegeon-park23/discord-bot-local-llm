import discord
import os
import re
import json
import asyncio
import datetime
import subprocess
import aiohttp
import glob
from openai import OpenAI
from playwright.async_api import async_playwright
import trafilatura
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# [CONFIG] 환경 변수 로드
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
INPUT_CHANNEL_ID = int(os.getenv("INPUT_CHANNEL_ID"))
OUTPUT_CHANNEL_ID = int(os.getenv("OUTPUT_CHANNEL_ID"))
MANAGEMENT_CHANNEL_ID = int(os.getenv("MANAGEMENT_CHANNEL_ID"))
LLM_HOST = os.getenv("LLM_HOST", "http://host.docker.internal:1234/v1")
SAVE_DIR = "/app/data"

# [CLASS] 구글 드라이브 업로더
class DriveUploader:
    def __init__(self):
        self.drive = None
        self.folder_id = None
        self.folder_name = "NotebookLM_Source"
        self._login()

    def _login(self):
        try:
            gauth = GoogleAuth()
            # Docker 컨테이너 내 경로 지정
            gauth.LoadCredentialsFile("/app/mycreds.txt")
            if gauth.credentials is None:
                print("[Drive] ⚠️ 인증 파일(mycreds.txt)이 없습니다. 드라이브 기능을 비활성화합니다.")
                return
            
            if gauth.access_token_expired:
                gauth.Refresh()
            else:
                gauth.Authorize()
            
            self.drive = GoogleDrive(gauth)
            print("[Drive] ✅ Google Drive 로그인 성공!")
            self._get_or_create_folder()
        except Exception as e:
            print(f"[Drive] ❌ 로그인 실패: {e}")

    def _get_or_create_folder(self):
        if not self.drive: return
        try:
            file_list = self.drive.ListFile({'q': f"title='{self.folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
            if file_list:
                self.folder_id = file_list[0]['id']
                print(f"[Drive] 폴더 연결됨: {self.folder_name} ({self.folder_id})")
            else:
                folder = self.drive.CreateFile({'title': self.folder_name, 'mimeType': 'application/vnd.google-apps.folder'})
                folder.Upload()
                self.folder_id = folder['id']
                print(f"[Drive] 새 폴더 생성됨: {self.folder_name} ({self.folder_id})")
        except Exception as e:
            print(f"[Drive] 폴더 에러: {e}")

    def upload(self, filepath, title):
        if not self.drive or not self.folder_id: return False
        try:
            filename = os.path.basename(filepath)
            file_drive = self.drive.CreateFile({
                'title': filename,
                'parents': [{'id': self.folder_id}]
            })
            file_drive.SetContentFile(filepath)
            file_drive.Upload()
            print(f"[Drive] 📤 업로드 성공: {filename}")
            return True
        except Exception as e:
            print(f"[Drive] ❌ 업로드 실패: {e}")
            return False

# [CLASS] 콘텐츠 추출기
class ContentExtractor:
    @staticmethod
    def normalize_url(url):
        url = re.sub(r"(https?://)(fxfxtwitter|fxtwitter|vxtwitter|fixupx|twittpr)(\.com/)", r"\1x\3", url)
        if "threads.com" in url or "threads.net" in url:
            url = url.replace("threads.com", "threads.net").split("?")[0]
        return url

    @staticmethod
    async def extract_dynamic_content(url):
        print(f"[Playwright] Scraping: {url}")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="ko-KR"
                )
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    try: await page.wait_for_load_state("networkidle", timeout=5000)
                    except: pass
                    
                    content = await page.content()
                    extracted_text = trafilatura.extract(content, include_comments=False)
                    
                    if not extracted_text:
                        desc = await page.get_attribute('meta[property="og:description"]', 'content')
                        title = await page.title()
                        if desc: extracted_text = f"제목: {title}\n내용: {desc}"
                    return extracted_text
                finally:
                    await browser.close()
        except Exception as e:
            print(f"[Playwright Error] {e}")
            return None

    @staticmethod
    def _extract_youtube_sync(url):
        print(f"[YouTube] Processing: {url}")
        try:
            video_id = None
            if "v=" in url: video_id = url.split("v=")[1].split("&")[0]
            elif "youtu.be" in url: video_id = url.split("/")[-1].split("?")[0]
            if not video_id: return {"error": "Invalid YouTube URL"}

            cmd = ["yt-dlp", "--write-auto-sub", "--write-sub", "--sub-lang", "ko,en", "--skip-download", "--output", f"/app/data/%(id)s", url]
            subprocess.run(cmd, check=True, capture_output=True)
            
            target_base = f"/app/data/{video_id}"
            content = ""
            for lang in ['.ko.vtt', '.en.vtt']:
                path = target_base + lang
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        text_lines = [line.strip() for line in lines if '-->' not in line and line.strip() != 'WEBVTT' and line.strip()]
                        content = " ".join(dict.fromkeys(text_lines))
                    os.remove(path)
                    break
            if content: return {"type": "YouTube", "content": content[:7000]}
            return {"error": "자막을 찾을 수 없습니다."}
        except Exception as e:
            return {"error": f"YouTube Error: {str(e)}"}

    @staticmethod
    async def extract(url):
        url = ContentExtractor.normalize_url(url)
        print(f"[Extractor] Normalized URL: {url}")
        if "youtube.com" in url or "youtu.be" in url:
            return await asyncio.to_thread(ContentExtractor._extract_youtube_sync, url)
        content = await ContentExtractor.extract_dynamic_content(url)
        if not content or len(content.strip()) < 50:
             return {"error": "본문 추출 실패"}
        source_type = "X/Threads" if "x.com" in url or "threads.net" in url else "Web"
        return {"type": source_type, "content": content[:7000]}

# [CLASS] AI 에이전트
class AIAgent:
    def __init__(self):
        print(f"[AI] Connecting to LLM at {LLM_HOST}")
        self.client = OpenAI(base_url=LLM_HOST, api_key="lm-studio")

    def analyze(self, text):
        if not text or len(text) < 50: return None
        system_prompt = """
You are a technical content summarizer.
Analyze the provided text and output ONLY valid JSON.
Format: {"title":"Korean Title","summary":"3 bullet points in Korean","category":"Tech/AI/Eco","tags":["tag1"],"difficulty":"Easy/Med/Hard"}
"""
        try:
            safe_text = text[:7000]
            response = self.client.chat.completions.create(
                model="local-model",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Text:\n{safe_text}"}],
                temperature=0.1,
            )
            content = response.choices[0].message.content
            clean_json = content.replace("```json", "").replace("```", "").strip()
            start, end = clean_json.find('{'), clean_json.rfind('}') + 1
            if start != -1 and end != -1: clean_json = clean_json[start:end]
            return json.loads(clean_json)
        except Exception as e:
            print(f"[AI Error] {e}")
            return None

    def deep_dive(self, text):
        if not text or len(text) < 50: return None
        system_prompt = """
You are a Senior Technical Researcher. 
Conduct a comprehensive Deep Dive analysis of the provided text.
Output MUST be in Korean Markdown format.
Structure:
# [Title]
## 1. 🔍 핵심 논거 및 인사이트
## 2. ⚙️ 기술적 심층 분석
## 3. ⚖️ 비판적 시각
## 4. 🚀 실무 적용 포인트
"""
        try:
            safe_text = text[:12000]
            response = self.client.chat.completions.create(
                model="local-model",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Analyze:\n{safe_text}"}],
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[AI DeepDive Error] {e}")
            return None

# [CLASS] 디스코드 봇 메인
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

    # ------------------------------------------------------------------
    # [EVENT] 심층 분석 (이모지 반응)
    # ------------------------------------------------------------------
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.user.id: return
        
        print(f"[Event] Reaction: {payload.emoji}")
        target_emojis = ["🕵️‍♂️", "🕵️", "🕵", "🔍"]
        
        if str(payload.emoji) in target_emojis:
            channel = self.get_channel(payload.channel_id)
            if not channel: return
            try: message = await channel.fetch_message(payload.message_id)
            except: return

            print(f"[DeepDive] 심층 분석 시작")
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

                # Drive Upload
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

    # ------------------------------------------------------------------
    # [EVENT] 메시지 처리 핸들러 (명령어 및 링크 수집)
    # ------------------------------------------------------------------
    async def on_message(self, message):
        if message.author == self.user: return

        # 1. 관리 채널 명령어
        if message.channel.id == MANAGEMENT_CHANNEL_ID:
            if "!url" in message.content or "주소" in message.content:
                await self.send_ngrok_url(message.channel.id)
            elif message.content.startswith("!weekly"):
                await self._handle_weekly_report(message)
            elif message.content.startswith("!ask"):
                await self._handle_ask_question(message)
            return

        # 2. 링크 입력 채널
        if message.channel.id == INPUT_CHANNEL_ID:
            await self._handle_link_submission(message)

    # ------------------------------------------------------------------
    # [HELPER] 기능별 로직 분리 (가독성 및 유지보수용)
    # ------------------------------------------------------------------
    async def _handle_weekly_report(self, message):
        await message.channel.send("📅 **주간 리포트** 생성 중...")
        report_files = []
        today = datetime.datetime.now()
        files = glob.glob(os.path.join(SAVE_DIR, "*.md"))
        
        for f in files:
            # DeepDive 파일은 중복 방지를 위해 제외 (선택 사항)
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
            
            # 파일 저장
            filename = f"Weekly_Report_{today.strftime('%Y%m%d')}.md"
            filepath = os.path.join(SAVE_DIR, filename)
            with open(filepath, "w", encoding='utf-8') as f: f.write(report)
            
            # Drive Upload
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

        # [DRIVE] 업로드
        self.uploader.upload(filepath, data.get('title'))

        await message.remove_reaction("👀", self.user)
        await message.add_reaction("✅")
        
        out_ch = self.get_channel(OUTPUT_CHANNEL_ID)
        if out_ch:
            embed = discord.Embed(title=data.get('title'), url=url, color=0x00ff00)
            embed.add_field(name="요약", value=summary, inline=False)
            embed.set_footer(text="Local LLM • Drive Uploaded")
            await out_ch.send(embed=embed)

if __name__ == "__main__":
    bot = KnowledgeBot()
    bot.run(DISCORD_TOKEN)
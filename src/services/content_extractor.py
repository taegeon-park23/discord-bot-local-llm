import os
import re
import asyncio
import subprocess
from playwright.async_api import async_playwright
import trafilatura

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
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="ko-KR"
                )
                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
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
            
            # 쿠키 파일이 있으면 사용 (429 에러 방지)
            if os.path.exists("/app/cookies.txt"):
                cmd.extend(["--cookies", "/app/cookies.txt"])
            
            # User-Agent 설정 (봇 탐지 우회)
            cmd.extend(["--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"])

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

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            print(f"[YouTube Error] {error_msg}")
            return {"error": f"YouTube download failed: {error_msg[:200]}..."}
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

# Microsoft Playwright 공식 이미지 (Python 포함, 브라우저 의존성 해결됨)
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# yt-dlp 실행을 위한 ffmpeg 및 필수 유틸 설치
RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 브라우저 설치 (Chromium만 설치하여 용량 절약)
RUN playwright install chromium

# 소스코드 및 쿠키 파일 복사
COPY main.py .
COPY src/ ./src/
# 쿠키 파일이 없을 경우를 대비해 빈 파일 생성 (선택 사항)
# RUN touch cookies.txt

CMD ["python", "main.py"]
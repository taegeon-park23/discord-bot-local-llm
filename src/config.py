import os

# [CONFIG] 환경 변수 로드
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
INPUT_CHANNEL_ID = int(os.getenv("INPUT_CHANNEL_ID", "0"))
OUTPUT_CHANNEL_ID = int(os.getenv("OUTPUT_CHANNEL_ID", "0"))
MANAGEMENT_CHANNEL_ID = int(os.getenv("MANAGEMENT_CHANNEL_ID", "0"))
LLM_HOST = os.getenv("LLM_HOST", "http://host.docker.internal:1234/v1")
SAVE_DIR = "/app/data"

# Gemini API 설정
GEMINI_API_KEYS = os.getenv("GEMINI_API_KEYS", "").split(",")
GEMINI_API_KEYS = [k.strip() for k in GEMINI_API_KEYS if k.strip()]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

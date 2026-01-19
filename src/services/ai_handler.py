import json
from openai import OpenAI
from src.config import LLM_HOST

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

import json
from openai import OpenAI
from src.config import LLM_HOST, GEMINI_API_KEYS, GEMINI_MODEL
from src.logger import get_logger

logger = get_logger(__name__)

class AIAgent:
    def __init__(self):
        self.gemini_keys = GEMINI_API_KEYS
        self.local_url = LLM_HOST
        # Gemini OpenAI 호환 엔드포인트
        self.gemini_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        
        logger.info(f"[AI] 초기화: Gemini 키 {len(self.gemini_keys)}개 감지, Local Fallback: {self.local_url}")

    def _get_client(self, is_local=False, api_key=None):
        """상황에 맞는 OpenAI 클라이언트를 생성하여 반환"""
        if is_local:
            return OpenAI(base_url=self.local_url, api_key="lm-studio")
        else:
            return OpenAI(base_url=self.gemini_base_url, api_key=api_key)

    def _call_llm_with_failover(self, messages, temperature=0.1):
        """
        [Failover 전략]
        1. Gemini Key 리스트를 순회하며 시도
        2. 모든 Gemini Key 실패 시 -> Local LLM 시도
        3. Local LLM 실패 시 -> None 반환
        """
        
        # 1. Gemini API 시도 (Key Rotation)
        for idx, key in enumerate(self.gemini_keys):
            try:
                client = self._get_client(is_local=False, api_key=key)
                logger.info(f"[AI] Gemini API 시도 (Key #{idx+1})")
                
                response = client.chat.completions.create(
                    model=GEMINI_MODEL,
                    messages=messages,
                    temperature=temperature
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"[AI] Gemini (Key #{idx+1}) 실패: {e}")
                continue # 다음 키 시도

        # 2. Local LLM Fallback
        logger.warning("[AI] ⚠️ 모든 Gemini API 실패. Local LLM으로 전환합니다.")
        try:
            client = self._get_client(is_local=True)
            response = client.chat.completions.create(
                model="local-model",
                messages=messages,
                temperature=temperature
            )
            logger.info("[AI] Local LLM 응답 성공")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"[AI] ❌ Local LLM마저 실패했습니다: {e}")
            return None

    def analyze(self, text):
        if not text or len(text) < 50: return None
        
        # Load valid topics from YAML source of truth
        import yaml
        topics_str = ""
        try:
            with open("src/data/tag_mapping.yaml", "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                valid_topics = [item['topic'] for item in data.get('mappings', [])]
                topics_str = ", ".join(valid_topics)
        except:
             # Fallback if file read fails
            topics_str = "Development, AI & ML, Design, Trends & News, Uncategorized"

        system_prompt = f"""
You are a technical content summarizer.
Analyze the provided text and output ONLY valid JSON.
Choose 'category' STRICTLY from this list: [{topics_str}]
Format: {{"title":"Korean Title","summary":"3 bullet points in Korean","category":"One of the topics above","tags":["tag1", "tag2"],"difficulty":"Easy/Med/Hard"}}
"""
        messages = [            
            {"role": "user", "content": f"{system_prompt}\n\n--- Input Text ---\n{text[:15000]}"}
        ]

        content = self._call_llm_with_failover(messages, temperature=0.1)
        
        if not content: return None

        try:
            # JSON 파싱 보정
            clean_json = content.replace("```json", "").replace("```", "").strip()
            start, end = clean_json.find('{'), clean_json.rfind('}') + 1
            if start != -1 and end != -1: clean_json = clean_json[start:end]
            
            result = json.loads(clean_json)
            
            # Tag Normalization
            from src.services.tag_manager import TagManager
            tag_manager = TagManager()
            original_tags = result.get('tags', [])
            if original_tags:
                result['topics'] = tag_manager.normalize_tags(original_tags)
                # Option: Overwrite tags or keep both. Keeping both for now as per plan flexibility.
                # result['tags'] = result['topics'] 
            
            return result
        except Exception as e:
            logger.error(f"[AI] JSON 파싱 실패: {e}")
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
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze:\n{text[:30000]}"} # Gemini Long Context 대폭 활용
        ]

        return self._call_llm_with_failover(messages, temperature=0.3)

    def chat(self, messages, temperature=0.1):
        """Standard chat interface with failover support"""
        return self._call_llm_with_failover(messages, temperature)

    def generate_tags(self, text):
        """
        Generates relevant tags from the provided text.
        Returns a list of normalized tag strings.
        """
        if not text or len(text) < 50: 
            return []
        
        # Load valid topics for guidance
        import yaml
        topics_hint = ""
        try:
            with open("src/data/tag_mapping.yaml", "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                valid_topics = [item['topic'] for item in data.get('mappings', [])]
                topics_hint = ", ".join(valid_topics)
        except:
            topics_hint = "Development, AI & ML, Design, Trends & News"
        
        system_prompt = f"""
You are a technical content analyzer.
Extract 5-10 relevant tags/keywords from the provided text.
Prefer tags related to these topics: [{topics_hint}]
Output MUST be ONLY a valid JSON array of strings.
Example: ["python", "asyncio", "discord", "bot"]
"""
        messages = [
            {"role": "user", "content": f"{system_prompt}\n\n--- Text ---\n{text[:8000]}"}
        ]
        
        content = self._call_llm_with_failover(messages, temperature=0.1)
        
        if not content:
            logger.warning("[AI] Tag generation failed - LLM returned empty")
            return []
        
        try:
            # Parse JSON
            clean_json = content.replace("```json", "").replace("```", "").strip()
            start = clean_json.find('[')
            end = clean_json.rfind(']') + 1
            if start != -1 and end != 0:
                clean_json = clean_json[start:end]
            
            raw_tags = json.loads(clean_json)
            
            if not isinstance(raw_tags, list):
                logger.warning(f"[AI] Tag generation returned non-list: {type(raw_tags)}")
                return []
            
            # Normalize tags using TagManager
            from src.services.tag_manager import TagManager
            tag_manager = TagManager()
            normalized_tags = tag_manager.normalize_tags([str(t) for t in raw_tags])
            
            # Force all tags to lowercase to prevent case sensitivity issues
            lowercase_tags = [tag.lower() for tag in normalized_tags]
            
            logger.info(f"[AI] Generated {len(lowercase_tags)} tags: {lowercase_tags}")
            return lowercase_tags
            
        except json.JSONDecodeError as e:
            logger.error(f"[AI] Tag JSON parsing failed: {e}, content: {content[:200]}")
            return []
        except Exception as e:
            logger.error(f"[AI] Tag generation error: {e}")
            return []

    def generate_embedding(self, text):
        """Generates embedding for given text using Gemini Text Embedding 004"""
        if not text: return None
        
        # Key Rotation for Embeddings
        for idx, key in enumerate(self.gemini_keys):
            try:
                client = self._get_client(is_local=False, api_key=key)
                # Note: openai-python wrapper for Gemini supports embeddings.create
                # Model name: text-embedding-004
                response = client.embeddings.create(
                    input=text,
                    model="text-embedding-004"
                )
                return response.data[0].embedding
            except Exception as e:
                logger.warning(f"[AI] Embedding (Key #{idx+1}) 실패: {e}")
                continue 
        
        logger.error("[AI] ❌ 모든 Embedding 생성 실패")
        return None

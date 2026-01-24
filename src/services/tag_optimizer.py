
import os
import asyncio
import yaml
from sqlalchemy.future import select
from src.database.engine import AsyncSessionLocal
from src.database.models import Document
from src.services.ai_handler import AIAgent
from src.logger import get_logger

logger = get_logger("TagOptimizationService")

class TagOptimizationService:
    def __init__(self, mapping_file: str = "src/data/tag_mapping.yaml"):
        self.mapping_file = mapping_file
        # Ensure path is absolute or correct relative to project root
        if not os.path.exists(self.mapping_file):
             # Try relative to CWD if not found directly
             if os.path.exists(os.path.join(os.getcwd(), self.mapping_file)):
                 self.mapping_file = os.path.join(os.getcwd(), self.mapping_file)

    async def optimize(self) -> dict:
        """
        Main execution method:
        1. Fetch unmapped tags from DB.
        2. Get LLM suggestions.
        3. Merge into YAML.
        
        Returns:
            dict: Summary of changes (e.g., {"updated": 5, "new_topics": 2})
        """
        logger.info("🚀 Starting Tag Optimization...")
        
        # 1. Fetch DB Tags
        unmapped_tags = await self._fetch_unmapped_tags()
        if not unmapped_tags:
            logger.info("✅ No unmapped tags found.")
            return {"status": "no_changes", "message": "No unmapped tags found"}
            
        logger.info(f"🧐 Found {len(unmapped_tags)} unmapped tags: {unmapped_tags}")

        # 2. Ask LLM
        agent = AIAgent()
        current_mappings = self._load_mappings()
        
        # Prepare context for LLM
        mappings_context = ""
        for group in current_mappings:
            topic = group.get('topic', 'Unknown')
            synonyms = group.get('synonyms', [])
            mappings_context += f"- {topic}: {synonyms}\n"

        prompt = f"""
You are a Taxonomy Specialist.
Here are current topic mappings (Topic: [synonyms]):
{mappings_context}

Here are NEW unmapped tags found in database:
{unmapped_tags}

Task:
1. For each new tag, assign it to an EXISTING topic if appropriate.
2. If it fits none, suggest a NEW topic name.
3. Output ONLY a YAML snippet representing the UPDATED structure.
   - Format: return a list of objects where keys are topics and values are lists of new tags to add.
   - Example:
     ```yaml
     mappings:
       - Development:
         - react
         - nextjs
       - New Topic Name:
         - strange tag
     ```
"""
        messages = [{"role": "user", "content": prompt}]
        
        logger.info("🧠 Consulting with LLM...")
        response = agent.chat(messages, temperature=0.1)
        
        if not response:
            logger.error("❌ LLM failed to respond.")
            return {"status": "error", "message": "LLM failed to respond"}

        # 3. Apply Suggestions
        summary = self._apply_suggestions(response, current_mappings)
        return summary

    async def _fetch_unmapped_tags(self):
        """Fetches all unique tags from DB that are NOT in the current YAML."""
        # Load current known tags
        current_mappings = self._load_mappings()
        known_tags = set()
        for group in current_mappings:
            topic = group.get('topic', '')
            if topic: known_tags.add(topic.lower())
            for s in group.get('synonyms', []):
                known_tags.add(str(s).lower())

        # Fetch all tags from DB
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Document.tags))
            all_tags_lists = result.scalars().all()
            
            db_tags = set()
            for tags in all_tags_lists:
                if tags:
                    for tag in tags:
                        if isinstance(tag, str):
                            db_tags.add(tag.lower())
        
        # Diff
        return [tag for tag in db_tags if tag not in known_tags]

    def _load_mappings(self):
        """Loads existing tag mappings."""
        if not os.path.exists(self.mapping_file):
            return []
        with open(self.mapping_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data.get('mappings', []) if data else []

    def _apply_suggestions(self, llm_response: str, current_mappings: list) -> dict:
        """Parses LLM response and updates the YAML file."""
        # Clean Markdown
        clean_yaml = llm_response.replace("```yaml", "").replace("```", "").strip()
        
        try:
            suggestions_data = yaml.safe_load(clean_yaml)
            suggested_mappings = suggestions_data.get('mappings', []) if suggestions_data else []
        except Exception as e:
            logger.error(f"Failed to parse LLM YAML: {e}")
            return {"status": "error", "message": f"YAML Parse Error: {e}"}

        topic_map = {}
        for idx, item in enumerate(current_mappings):
            t_name = item.get('topic')
            if t_name:
                topic_map[t_name.lower()] = {
                    'index': idx,
                    'synonyms': set(s.lower() for s in item.get('synonyms', [])),
                    'original_topic': t_name
                }

        updates_count = 0
        new_topics_count = 0

        for item in suggested_mappings:
            if isinstance(item, dict):
                for topic, tags in item.items():
                    if not tags: continue
                    
                    topic_key = topic.strip().lower()
                    new_tags = set(str(t).lower() for t in tags if t)
                    
                    if topic_key in topic_map:
                        # Update existing
                        entry = topic_map[topic_key]
                        idx = entry['index']
                        current_synonyms = entry['synonyms']
                        
                        to_add = [t for t in new_tags if t not in current_synonyms]
                        if to_add:
                            if 'synonyms' not in current_mappings[idx]:
                                current_mappings[idx]['synonyms'] = []
                            current_mappings[idx]['synonyms'].extend(to_add)
                            updates_count += 1
                    else:
                        # New Topic
                        new_entry = {
                            'topic': topic.strip(),
                            'synonyms': list(new_tags)
                        }
                        current_mappings.append(new_entry)
                        topic_map[topic_key] = {'index': -1, 'synonyms': new_tags} # placeholder
                        new_topics_count += 1

        if updates_count > 0 or new_topics_count > 0:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                yaml.dump({'version': 1.0, 'mappings': current_mappings}, f, allow_unicode=True, sort_keys=False)
            logger.info(f"💾 Updated {updates_count} topics and created {new_topics_count} new topics.")
            return {"status": "success", "updated": updates_count, "new_topics": new_topics_count}
        
        return {"status": "no_changes", "message": "No new valid mappings found in suggestion"}

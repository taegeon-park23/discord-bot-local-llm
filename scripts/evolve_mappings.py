
import asyncio
import sys
import os
import yaml
import logging

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from sqlalchemy.future import select
from src.database.engine import AsyncSessionLocal
from src.database.models import Document
from src.services.ai_handler import AIAgent
from src.logger import get_logger

# Setup Logger
logger = get_logger("TagEvolution")
logging.basicConfig(level=logging.INFO)

TAG_MAPPING_FILE = os.path.join(project_root, "src/data/tag_mapping.yaml")

async def fetch_uncategorized_tags():
    """Fetches all unique tags from the database."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document.tags))
        all_tags_lists = result.scalars().all()
        
        all_tags = set()
        for tags in all_tags_lists:
            if tags:
                for tag in tags:
                    if isinstance(tag, str):
                        all_tags.add(tag.lower())
        return all_tags

def load_mappings():
    """Loads existing tag mappings."""
    if not os.path.exists(TAG_MAPPING_FILE):
        logger.warning(f"Mapping file not found at {TAG_MAPPING_FILE}")
        return []
    with open(TAG_MAPPING_FILE, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        return data.get('mappings', [])

def identify_unknown_tags(all_tags, mappings):
    """Identifies tags that are not present in the current mappings."""
    known_tags = set()
    for group in mappings:
        topic = group.get('topic', '')
        if topic:
            known_tags.add(topic.lower())
        
        if group.get('synonyms'):
            for s in group['synonyms']:
                known_tags.add(s.lower())
    
    unknown = []
    for tag in all_tags:
        if tag not in known_tags:
            unknown.append(tag)
    return unknown

async def main():
    print("🚀 Starting Tag Evolution Protocol...")
    
    # 1. Fetch DB Tags
    try:
        db_tags = await fetch_uncategorized_tags()
        print(f"📊 Found {len(db_tags)} unique tags in Database.")
    except Exception as e:
        print(f"❌ Failed to fetch tags from DB: {e}")
        return

    # 2. Load Mapping
    mappings = load_mappings()
    print(f"📚 Loaded {len(mappings)} topic mappings.")
    
    # 3. Identify Unknowns
    unknown_tags = identify_unknown_tags(db_tags, mappings)
    
    if not unknown_tags:
        print("✅ No unmapped tags found. System is clean.")
        return

    print(f"🧐 Found {len(unknown_tags)} unmapped tags: {unknown_tags}")
    
    # 4. Ask LLM
    agent = AIAgent()
    
    mappings_context = ""
    for group in mappings:
        topic = group.get('topic', 'Unknown')
        synonyms = group.get('synonyms', [])
        mappings_context += f"- {topic}: {synonyms}\n"

    prompt = f"""
You are a Taxonomy Specialist.
Here are current topic mappings (Topic: [synonyms]):
{mappings_context}

Here are NEW unmapped tags found in the wild:
{unknown_tags}

Task:
1. For each new tag, suggest which EXISTING topic it belongs to.
2. If it fits none, suggest a NEW topic name.
3. Output a YAML snippet representing the UPDATED structure.
   - For existing topics, just list the new synonyms to add (don't repeat all existing ones if not necessary, but context helps).
   - Actually, just provide the 'mappings' list with relevant updates or new entries.
4. Format MUST be valid YAML.
"""
    
    messages = [{"role": "user", "content": prompt}]
    
    print("🧠 Consulting with LLM...")
    try:
        response = agent.chat(messages, temperature=0.1)
        
        if response:
            print("\n🤖 LLM Suggestion:\n")
            print(response)
            
            output_file = os.path.join(project_root, "src/data/suggested_mappings.yaml")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(response)
            print(f"\n💾 Saved suggestion to '{output_file}'. Implementation requires manual review.")
        else:
            print("❌ LLM failed to respond.")
    except Exception as e:
        print(f"❌ Error during LLM consultation: {e}")

if __name__ == "__main__":
    asyncio.run(main())

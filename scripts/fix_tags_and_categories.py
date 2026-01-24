import sys
import os
import asyncio
import argparse
import yaml
import re # Added regex import
from pathlib import Path
from sqlalchemy.future import select
from sqlalchemy import or_, func

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.database.engine import AsyncSessionLocal
from src.database.models import Document
from src.services.ai_handler import AIAgent
from src.services.tag_manager import TagManager
from src.logger import get_logger

logger = get_logger(__name__)

# Constants
TAG_MAPPING_FILE = "src/data/tag_mapping.yaml"

def load_yaml(file_path):
    if not os.path.exists(file_path):
        return {"version": "1.0", "mappings": []}
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def save_yaml(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

async def process_documents(dry_run, limit):
    logger.info(f"Starting document categorization. Dry Run: {dry_run}, Limit: {limit}")
    
    tag_manager = TagManager(TAG_MAPPING_FILE)
    ai_agent = AIAgent()
    
    # Reload mappings just in case
    tag_manager.reload()
    current_mappings = tag_manager.mappings

    async with AsyncSessionLocal() as db:
        # Fetch target documents
        # Tags is empty OR is an empty list
        stmt = select(Document).where(
            or_(
                Document.tags == None,
                func.jsonb_array_length(Document.tags) == 0
            )
        ).limit(limit)
        
        result = await db.execute(stmt)
        documents = result.scalars().all()
        
        logger.info(f"Found {len(documents)} documents to process.")
        
        updated_count = 0
        
        for doc in documents:
            logger.info(f"Processing Doc ID {doc.id}: '{doc.title}' ({doc.local_file_path})")
            
            # Read file content safely
            content = ""
            try:
                if os.path.exists(doc.local_file_path):
                     with open(doc.local_file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(2048) # Read first 2KB
                else:
                    logger.warning(f"File not found: {doc.local_file_path}")
            except Exception as e:
                logger.error(f"Error reading file {doc.local_file_path}: {e}")
                continue

            # Step 1: Deterministic Keyword Matching
            img_tags = []
            matched_category = None
            
            # Use TagManager's logic, but we need to check raw content too if title fails
            # But the requirement says "Check content/title against tag_mapping.yaml synonyms"
            
            # 1. Check Title
            doc_tags_from_title = _extract_tags_from_text(doc.title, current_mappings)
            if doc_tags_from_title:
                 # Infer category
                 matched_category = tag_manager.get_category_from_tags(doc_tags_from_title)
                 img_tags = doc_tags_from_title
                 logger.info(f" -> Matched via Title: {matched_category} (Tags: {img_tags})")

            # 2. Check Content (if not matched yet)
            if not matched_category and content:
                 doc_tags_from_content = _extract_tags_from_text(content, current_mappings)
                 if doc_tags_from_content:
                     matched_category = tag_manager.get_category_from_tags(doc_tags_from_content)
                     img_tags = doc_tags_from_content
                     logger.info(f" -> Matched via Content: {matched_category} (Tags: {img_tags})")
            
            # Step 2: LLM Fallback
            new_category_proposed = False
            if not matched_category:
                logger.info(f" -> No keyword match. invoking LLM...")
                
                # Construct Prompt
                known_topics = [m['topic'] for m in current_mappings]
                prompt_text = f"""
                Analyze the following text details and assign a Category and Tags.
                
                Input:
                Title: {doc.title}
                Snippet: {content[:500]}
                
                Existing Categories: {", ".join(known_topics)}
                
                Task:
                1. If it fits an existing category, return that category.
                2. If it is a completely new topic (e.g., 'Blockchain', 'IoT'), propose a NEW category name.
                3. Extract 2-3 relevant tags (synonyms).
                
                Output JSON ONLY: {{"category": "Str", "tags": ["Str", "Str"], "is_new_category": true/false}}
                """
                
                response = ai_agent.chat([{ "role": "user", "content": prompt_text }], temperature=0.0)
                
                try:
                    import json
                    # Naive cleanup
                    clean_res = response.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_res)
                    
                    matched_category = data.get("category")
                    img_tags = data.get("tags", [])
                    new_category_proposed = data.get("is_new_category", False)
                    
                    logger.info(f" -> LLM Result: {matched_category}, New: {new_category_proposed}")
                    
                except Exception as e:
                    logger.error(f"LLM Parsing failed: {e}")
                    matched_category = "Uncategorized"
            
            # Step 3: Action
            if matched_category and matched_category != "Uncategorized":
                
                # 3.1 Handle New Category
                if new_category_proposed:
                     exists = False
                     for m in current_mappings:
                         if m['topic'].lower() == matched_category.lower():
                             exists = True
                             # Merge tags
                             existing_syns = set(m['synonyms'])
                             existing_syns.update([t.lower() for t in img_tags])
                             m['synonyms'] = list(existing_syns)
                             break
                     
                     if not exists:
                         logger.info(f"[NEW CATEGORY] Adding '{matched_category}' to YAML")
                         new_entry = {
                             "topic": matched_category,
                             "synonyms": [t.lower() for t in img_tags]
                         }
                         current_mappings.append(new_entry)
                         
                     # Update YAML file
                     if not dry_run:
                          yaml_data = load_yaml(TAG_MAPPING_FILE)
                          yaml_data['mappings'] = current_mappings
                          save_yaml(TAG_MAPPING_FILE, yaml_data)
                          logger.info("Updated tag_mapping.yaml")
                     else:
                          logger.info("[Dry Run] Would update tag_mapping.yaml")

                # 3.2 Update DB
                # Ensure the Category explicitly appears in the tags so get_category_from_tags works
                if matched_category and matched_category not in img_tags:
                    img_tags.append(matched_category)

                normalized_tags = tag_manager.normalize_tags(img_tags)
                
                if not dry_run:
                    doc.tags = normalized_tags
                    db.add(doc)
                    logger.info(f" -> DB Updated: {doc.tags}")
                    updated_count += 1
                else:
                    logger.info(f" -> [Dry Run] Would update tags to: {normalized_tags}")
            
            else:
                 logger.info(" -> Could not determine category.")
        
        if not dry_run and updated_count > 0:
            await db.commit()
            logger.info(f"Committed {updated_count} changes to DB.")

def _extract_tags_from_text(text, mappings):
    """
    Scans text for any synonym in the mappings.
    Returns a list of FOUND synonyms.
    """
    found = set()
    text_lower = text.lower()
    
    for group in mappings:
        for synonym in group.get('synonyms', []):
            # Simple word boundary regex
            # Escape synonym to handle special chars like C++ or CI/CD
            pattern = r'\b' + re.escape(synonym.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found.add(synonym.lower())
    
    return list(found)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-categorize documents")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    parser.add_argument("--limit", type=int, default=50, help="Max documents to process")
    
    args = parser.parse_args()
    
    asyncio.run(process_documents(args.dry_run, args.limit))

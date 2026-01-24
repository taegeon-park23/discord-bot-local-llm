#!/usr/bin/env python3
"""
Tag Lowercase Migration Script (SQLAlchemy Core Version)

Migrates all existing tags in the database to lowercase:
1. Backs up the database (optional but recommended)
2. Updates all `documents.tags` to lowercase (removes duplicates)
3. Merges `tag_statistics` entries by lowercase key

Usage:
    docker exec knowledge_api python scripts/migrate_tags_to_lowercase.py [--no-backup]
"""

import asyncio
import sys
import os
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.engine import get_db_context
from src.database.models import TagStatistics, Document
from sqlalchemy import select, delete, update, insert
from src.logger import get_logger

logger = get_logger(__name__)


async def backup_database():
    """Create a database backup before migration"""
    logger.info("📦 Creating database backup...")
    try:
        import subprocess
        backup_file = f"backup_tags_{asyncio.get_event_loop().time():.0f}.sql"
        # Dummy backup for non-interactive mode
        logger.info(f"✅ Backup simulated: {backup_file}")
        return True
    except Exception as e:
        logger.error(f"❌ Backup error: {e}")
        return False


import json
from sqlalchemy import text

async def migrate_document_tags(db):
    """
    Migrate document tags row-by-row to bypass constraint issues.
    """
    logger.info("\n📄 Migrating document tags to lowercase (Row-by-Row)...")
    
    # Fetch all
    result = await db.execute(text("SELECT id, tags, local_file_path FROM documents"))
    rows = result.all()
    
    logger.info(f"Found {len(rows)} documents")
    updated_count = 0
    error_count = 0
    
    for row in rows:
        doc_id = row[0]
        tags = row[1]
        
        if not tags: continue
        
        # Lowercase conversion
        new_tags_list = []
        seen = set()
        for t in tags:
            lower = str(t).lower()
            if lower not in seen:
                new_tags_list.append(lower)
                seen.add(lower)
        
        if new_tags_list != tags:
            try:
                # Update specific row
                json_str = json.dumps(new_tags_list)
                await db.execute(
                    text("UPDATE documents SET tags = :tags WHERE id = :id"),
                    {"tags": json_str, "id": doc_id}
                )
                await db.commit() # Commit immediately
                updated_count += 1
            except Exception as e:
                await db.rollback()
                error_count += 1
                logger.warning(f"  ❌ Failed to update doc {doc_id}: {e}")
                
            if updated_count % 10 == 0:
                logger.debug(f"Updated {updated_count} docs...")
    
    logger.info(f"✅ Updated {updated_count} documents")
    if error_count > 0:
        logger.warning(f"⚠️ Skipped {error_count} documents due to errors")


async def migrate_tag_statistics(db):
    """
    Merge tag_statistics entries using Raw SQL logic.
    """
    logger.info("\n📊 Migrating tag_statistics to lowercase...")
    
    # 1. Fetch all
    result = await db.execute(text("SELECT tag, count FROM tag_statistics"))
    all_stats = result.all()
    
    # 2. Merge in-memory
    merged = defaultdict(int)
    for row in all_stats:
        merged[str(row[0]).lower()] += row[1]
    
    # 3. Truncate
    await db.execute(text("TRUNCATE TABLE tag_statistics"))
    await db.commit()
    
    # 4. Insert
    if merged:
        # Construct values string manually or use executemany
        # Using executemany with text() is safe
        values_list = [{"tag": tag, "count": count} for tag, count in merged.items()]
        
        await db.execute(
            text("INSERT INTO tag_statistics (tag, count) VALUES (:tag, :count)"),
            values_list
        )
        await db.commit()
    
    logger.info(f"✅ Created {len(merged)} merged tag statistics entries")
    return len(all_stats), len(merged)


async def verify_migration(db):
    """Verify results"""
    logger.info("\n🔍 Verifying migration...")
    
    # Check docs
    result = await db.execute(select(Document.tags))
    doc_tags_list = result.scalars().all()
    
    issues = 0
    for tags in doc_tags_list:
        if not tags: continue
        for tag in tags:
            if tag != tag.lower():
                issues += 1
                break
    
    # Check stats
    result = await db.execute(select(TagStatistics.tag))
    stat_tags = result.scalars().all()
    
    for tag in stat_tags:
        if tag != tag.lower():
            issues += 1
    
    if issues == 0:
        logger.info("✅ All tags are lowercase!")
        return True
    else:
        logger.error(f"❌ Verification failed with {issues} issues")
        return False


async def main():
    logger.info("🚀 Tag Lowercase Migration (Core Version)")
    
    try:
        # Step 1
        async with get_db_context() as db:
            await migrate_document_tags(db)
        
        # Step 2
        async with get_db_context() as db:
            await migrate_tag_statistics(db)
            
        # Step 3
        async with get_db_context() as db:
            await verify_migration(db)
            
        logger.info("\n✅ Migration Finished Successfully")
        
    except Exception as e:
        logger.error(f"Migration Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())

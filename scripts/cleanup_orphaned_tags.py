#!/usr/bin/env python3
"""
Orphaned Tag Cleanup Script

This script:
1. Fetches all tags from tag_statistics table
2. For each tag, checks if any document actually has this tag
3. Deletes tags that have no associated documents

Usage:
    docker exec knowledge_api python scripts/cleanup_orphaned_tags.py [--dry-run]
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.engine import get_db_context
from src.database.models import TagStatistics, Document
from sqlalchemy import select, delete, func
from src.logger import get_logger

logger = get_logger(__name__)


async def cleanup_orphaned_tags(dry_run: bool = True):
    """
    Find and remove tags from tag_statistics that don't exist in any document.
    
    Args:
        dry_run: If True, only report what would be deleted without actually deleting
    """
    logger.info("🧹 Starting orphaned tag cleanup...")
    logger.info(f"   Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will delete)'}")
    
    async with get_db_context() as db:
        # 1. Get all tags from tag_statistics
        stats_query = select(TagStatistics.tag, TagStatistics.count).order_by(TagStatistics.count.desc())
        stats_result = await db.execute(stats_query)
        all_stats_tags = stats_result.all()
        
        logger.info(f"\n📊 Found {len(all_stats_tags)} tags in tag_statistics table")
        
        # 2. Get all unique tags from documents (JSONB array)
        # We need to unnest the JSONB array to get individual tags
        from sqlalchemy import text
        
        # Query to extract all unique tags from documents
        doc_tags_query = text("""
            SELECT DISTINCT lower(tag_elem::text) as tag
            FROM documents, jsonb_array_elements_text(tags) as tag_elem
            WHERE tags IS NOT NULL AND jsonb_array_length(tags) > 0
        """)
        
        doc_tags_result = await db.execute(doc_tags_query)
        doc_tags_set = set(row[0].strip('"') for row in doc_tags_result)
        
        logger.info(f"📄 Found {len(doc_tags_set)} unique tags in documents")
        
        # 3. Find orphaned tags
        orphaned_tags = []
        mismatched_counts = []
        
        for tag_row in all_stats_tags:
            tag = tag_row[0]
            stats_count = tag_row[1]
            
            if tag not in doc_tags_set:
                orphaned_tags.append((tag, stats_count))
            else:
                # Verify the count is accurate
                count_query = text("""
                    SELECT COUNT(*)
                    FROM documents
                    WHERE tags @> :tag_json
                """)
                actual_count_result = await db.execute(
                    count_query,
                    {"tag_json": f'["{tag}"]'}
                )
                actual_count = actual_count_result.scalar()
                
                if actual_count != stats_count:
                    mismatched_counts.append((tag, stats_count, actual_count))
        
        # 4. Report findings
        if orphaned_tags:
            logger.warning(f"\n⚠️  Found {len(orphaned_tags)} orphaned tags:")
            for tag, count in orphaned_tags[:20]:  # Show first 20
                logger.warning(f"   - '{tag}' (count: {count})")
            if len(orphaned_tags) > 20:
                logger.warning(f"   ... and {len(orphaned_tags) - 20} more")
        else:
            logger.info("\n✅ No orphaned tags found!")
        
        if mismatched_counts:
            logger.warning(f"\n⚠️  Found {len(mismatched_counts)} tags with incorrect counts:")
            for tag, stats_count, actual_count in mismatched_counts[:10]:
                logger.warning(f"   - '{tag}': stats={stats_count}, actual={actual_count}")
            if len(mismatched_counts) > 10:
                logger.warning(f"   ... and {len(mismatched_counts) - 10} more")
        
        # 5. Delete orphaned tags
        if orphaned_tags and not dry_run:
            logger.info(f"\n🗑️  Deleting {len(orphaned_tags)} orphaned tags...")
            
            orphaned_tag_names = [tag for tag, _ in orphaned_tags]
            delete_stmt = delete(TagStatistics).where(TagStatistics.tag.in_(orphaned_tag_names))
            result = await db.execute(delete_stmt)
            await db.commit()
            
            logger.info(f"✅ Deleted {result.rowcount} orphaned tags from tag_statistics")
        elif orphaned_tags:
            logger.info(f"\n🔍 DRY RUN: Would delete {len(orphaned_tags)} orphaned tags")
        
        # 6. Fix mismatched counts
        if mismatched_counts and not dry_run:
            logger.info(f"\n🔧 Fixing {len(mismatched_counts)} tags with incorrect counts...")
            
            from sqlalchemy import update
            for tag, stats_count, actual_count in mismatched_counts:
                if actual_count == 0:
                    # Delete if actual count is 0
                    delete_stmt = delete(TagStatistics).where(TagStatistics.tag == tag)
                    await db.execute(delete_stmt)
                    logger.info(f"   Deleted '{tag}' (actual count is 0)")
                else:
                    # Update to correct count
                    update_stmt = (
                        update(TagStatistics)
                        .where(TagStatistics.tag == tag)
                        .values(count=actual_count)
                    )
                    await db.execute(update_stmt)
                    logger.info(f"   Updated '{tag}': {stats_count} -> {actual_count}")
            
            await db.commit()
            logger.info("✅ Counts updated successfully")
        elif mismatched_counts:
            logger.info(f"\n🔍 DRY RUN: Would fix {len(mismatched_counts)} tags with incorrect counts")


async def main():
    """Main entry point"""
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    if not dry_run:
        response = input("\n⚠️  This will DELETE orphaned tags. Continue? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Cancelled by user")
            return
    
    await cleanup_orphaned_tags(dry_run=dry_run)
    
    logger.info("\n✅ Cleanup script completed!")


if __name__ == "__main__":
    asyncio.run(main())

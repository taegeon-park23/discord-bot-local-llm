#!/usr/bin/env python3
"""
Reset Tag Statistics Script

This script resets the tag analytics state to allow full re-indexing:
1. Truncates `tag_statistics` table
2. Resets `batch_job_state` for 'tag_analytics' to 0

Usage:
    docker exec knowledge_api python scripts/reset_tag_analytics.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.engine import get_db_context
from src.database.models import TagStatistics, BatchJobState
from sqlalchemy import text, delete
from src.logger import get_logger

logger = get_logger(__name__)

async def reset_analytics():
    logger.info("🔄 Resetting Tag Analytics State...")
    
    async with get_db_context() as db:
        try:
            # 1. Truncate tag_statistics
            await db.execute(text("TRUNCATE TABLE tag_statistics"))
            logger.info("✅ Truncated 'tag_statistics' table")
            
            # 2. Reset BatchJobState
            # We can delete the row so it starts from scratch (get_last_processed_id returns 0 if not found)
            await db.execute(
                delete(BatchJobState).where(BatchJobState.job_name == "tag_analytics")
            )
            logger.info("✅ Reset 'tag_analytics' job state")
            
            await db.commit()
            logger.info("\n🎉 Reset Complete! Restart the backend to rebuild statistics.")
            
        except Exception as e:
            logger.error(f"❌ Reset failed: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(reset_analytics())

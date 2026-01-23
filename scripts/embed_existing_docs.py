
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy.future import select
from src.database.engine import get_db_context
from src.database.models import Document, DocumentChunk
from src.services.vector_service import VectorService
from src.logger import get_logger

logger = get_logger(__name__)

async def main():
    logger.info("Starting embedding backfill...")
    
    async with get_db_context() as db:
        # 1. Fetch all documents
        result = await db.execute(select(Document))
        documents = result.scalars().all()
        
        logger.info(f"Found {len(documents)} total documents.")
        
        vector_service = VectorService(db)
        
        for i, doc in enumerate(documents):
            # Check if chunks already exist
            existing_chunks_res = await db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
            )
            existing_chunks = existing_chunks_res.scalars().all()
            
            if existing_chunks:
                logger.info(f"[{i+1}/{len(documents)}] Doc {doc.id} already processed. Skipping.")
                continue

            logger.info(f"[{i+1}/{len(documents)}] Processing Doc {doc.id}: {doc.title}")
            
            # Read local file
            if not os.path.exists(doc.local_file_path):
                 logger.error(f"Doc {doc.id} Not Found at {doc.local_file_path}")
                 continue
            
            try:
                with open(doc.local_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                await vector_service.process_document(doc.id, content)
                logger.info(f"Doc {doc.id} processing complete.")
                
            except Exception as e:
                logger.error(f"Failed to process Doc {doc.id}: {e}")

    logger.info("Backfill completed.")

if __name__ == "__main__":
    asyncio.run(main())

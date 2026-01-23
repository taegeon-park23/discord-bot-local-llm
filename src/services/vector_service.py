from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.database.models import DocumentChunk
from src.services.ai_handler import AIAgent
from src.logger import get_logger

logger = get_logger(__name__)

class VectorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_agent = AIAgent()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )

    def chunk_text(self, text: str) -> List[str]:
        """Splits text into chunks using LangChain's RecursiveCharacterTextSplitter"""
        return self.text_splitter.split_text(text)

    async def process_document(self, doc_id: int, content: str):
        """Chunks document content, generates embeddings, and saves to DB"""
        if not content:
            logger.warning(f"[VectorService] Doc {doc_id} has no content.")
            return

        # 1. Chunk Text
        chunks = self.chunk_text(content)
        logger.info(f"[VectorService] Doc {doc_id}: Generated {len(chunks)} chunks.")

        # 2. Clear existing chunks (if re-processing)
        await self.clear_chunks(doc_id)

        # 3. Generate Embeddings & Save
        new_chunks = []
        for idx, chunk_text in enumerate(chunks):
            embedding = self.ai_agent.generate_embedding(chunk_text)
            if embedding:
                chunk_record = DocumentChunk(
                    document_id=doc_id,
                    chunk_index=idx,
                    content=chunk_text,
                    embedding=embedding
                )
                new_chunks.append(chunk_record)
            else:
                logger.error(f"[VectorService] Failed to generate embedding for Doc {doc_id} chunk {idx}")

        if new_chunks:
            self.db.add_all(new_chunks)
            await self.db.commit()
            logger.info(f"[VectorService] Doc {doc_id}: Saved {len(new_chunks)} vector chunks.")

    async def clear_chunks(self, doc_id: int):
        """Removes existing chunks for a document"""
        from sqlalchemy import delete
        await self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc_id))
        await self.db.commit()

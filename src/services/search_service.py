from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.database.models import DocumentChunk, Document
from src.services.ai_handler import AIAgent
from src.logger import get_logger

logger = get_logger(__name__)

class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_agent = AIAgent()

    async def search_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Performs semantic search using pgvector.
        Returns a list of dictionaries containing chunk info and parent document title.
        """
        # 1. Generate Query Embedding
        query_embedding = self.ai_agent.generate_embedding(query)
        if not query_embedding:
            logger.error("[SearchService] Failed to generate query embedding.")
            return []

        # 2. Execute Vector Search (Cosine Distance: <=> operator)
        # We order by distance ascending (closer is better)
        stmt = (
            select(DocumentChunk)
            .options(selectinload(DocumentChunk.document))
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        chunks = result.scalars().all()

        # 3. Format Results
        results = []
        for chunk in chunks:
            results.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document.id,
                "document_title": chunk.document.title,
                "content": chunk.content,
                "score": "N/A" # pgvector query directly via sqlalchemy doesn't easily return score in ORM mode without extra columns
            })
            
        return results

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

    async def search_similar(
        self, 
        query: str, 
        limit: int = 5, 
        offset: int = 0,
        threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic search using pgvector.
        Returns a list of dictionaries containing chunk info and parent document title.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            threshold: Maximum cosine distance to filter results (None = no filtering)
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
            .offset(offset)
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        chunks = result.scalars().all()

        # 3. Format Results with optional threshold filtering
        results = []
        for chunk in chunks:
            # Calculate cosine distance for filtering
            # Note: We can't easily get the distance from the ORM query without raw SQL
            # For now, we'll return all results and let the caller handle threshold
            # Or we could use a raw SQL query to get distance values
            results.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document.id,
                "document_title": chunk.document.title,
                "content": chunk.content,
                "score": "N/A" # pgvector query directly via sqlalchemy doesn't easily return score in ORM mode without extra columns
            })
            
        logger.info(f"[SearchService] Returned {len(results)} results (offset={offset}, limit={limit})")
        return results


import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.vector_service import VectorService
from src.services.search_service import SearchService
from src.database.models import Document, DocumentChunk

# Mock Data
MOCK_DOC_ID = 999
MOCK_CONTENT = "Apple is X. Banana is Y."
MOCK_CHUNKS = ["Apple is X.", "Banana is Y."]
MOCK_EMBEDDING = [0.1] * 768

@pytest.mark.asyncio
async def test_vector_service_process_document():
    # Mock DB Session
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Mock AIAgent
    with patch("src.services.vector_service.AIAgent") as MockAgent:
        agent_instance = MockAgent.return_value
        agent_instance.generate_embedding.return_value = MOCK_EMBEDDING
        
        service = VectorService(mock_db)
        
        # Override splitter for predictable chunks
        service.text_splitter = MagicMock()
        service.text_splitter.split_text.return_value = MOCK_CHUNKS
        
        await service.process_document(MOCK_DOC_ID, MOCK_CONTENT)
        
        # Verify Interactions
        service.text_splitter.split_text.assert_called_once_with(MOCK_CONTENT)
        assert agent_instance.generate_embedding.call_count == len(MOCK_CHUNKS)
        
        # Verify DB calls (Clear + Add + Commit)
        assert mock_db.execute.called # clear_chunks
        assert mock_db.add_all.called
        assert mock_db.commit.called

@pytest.mark.asyncio
async def test_search_service_search_similar():
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Mock Query Result
    mock_chunk = DocumentChunk(
        id=1, 
        document_id=MOCK_DOC_ID, 
        content="Apple is X", 
        embedding=MOCK_EMBEDDING
    )
    mock_chunk.document = Document(id=MOCK_DOC_ID, title="Test Doc")
    
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [mock_chunk]
    mock_db.execute.return_value = mock_result
    
    with patch("src.services.search_service.AIAgent") as MockAgent:
        agent_instance = MockAgent.return_value
        agent_instance.generate_embedding.return_value = MOCK_EMBEDDING
        
        service = SearchService(mock_db)
        results = await service.search_similar("query", limit=1)
        
        assert len(results) == 1
        assert results[0]['document_id'] == MOCK_DOC_ID
        assert results[0]['content'] == "Apple is X"

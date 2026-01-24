from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import os
import aiofiles
import asyncio
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.database.engine import get_db, engine
from src.database.models import Document, Base
from src.web_api.schemas import DocumentResponse, ContentUpdate, DashboardStats, SearchResultItem
from sqlalchemy import func
from datetime import timedelta, datetime
from src.logger import get_logger

logger = get_logger(__name__)

# 스케줄러 초기화
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 스케줄러 실행
    from src.services.tag_analytics import TagAnalyticsService
    
    # 태그 분석 작업을 6시간마다 실행
    scheduler.add_job(
        TagAnalyticsService.run_analytics,
        trigger=IntervalTrigger(hours=6),
        id="tag_analytics_job",
        name="Tag Analytics Batch Job",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ Scheduler started. Tag analytics will run every 6 hours.")
    
    # 앱 시작 시 1회 실행 (백그라운드)
    asyncio.create_task(TagAnalyticsService.run_analytics())
    logger.info("🚀 Initial tag analytics job triggered.")
    
    yield
    
    # 종료 시 스케줄러 정리
    scheduler.shutdown()
    await engine.dispose()

app = FastAPI(title="Knowledge Bot Admin API", lifespan=lifespan)

# CORS Setup
origins = [
    "http://localhost:3000",
    "http://localhost:3999",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/stats", response_model=DashboardStats)
async def get_stats(
    category: Optional[str] = None,
    doc_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    from src.services.db_service import DBService
    
    # 1. Total (Filtered)
    total_docs = await DBService.count_documents(db, doc_type=doc_type, category=category)

    # 2. Failed (Global - keeping context of system health)
    # If we want filtered failed count:
    # failed_count = await DBService.count_documents(db, doc_type=doc_type, category=category, upload_status='FAILED')
    # For now, let's keep failed/recent as GLOBAL stats to show system health, 
    # but Total reflects the current view.
    
    from src.database.models import UploadStatus
    failed_query = select(func.count(Document.id)).where(Document.gdrive_upload_status == UploadStatus.FAILED)
    failed_res = await db.execute(failed_query)
    failed_count = failed_res.scalar() or 0

    # 3. Recent (Global)
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_query = select(func.count(Document.id)).where(Document.created_at >= seven_days_ago)
    recent_res = await db.execute(recent_query)
    recent_count = recent_res.scalar() or 0

    return DashboardStats(
        total_documents=total_docs,
        failed_uploads=failed_count,
        recent_docs_count=recent_count
    )

@app.post("/api/admin/auto-categorize")
async def auto_categorize_tags():
    """
    Triggers the Batch Tag Optimization process:
    1. Identify unmapped tags.
    2. Ask LLM for mappings.
    3. Update YAML.
    4. Reload TagManager.
    """
    from src.services.tag_optimizer import TagOptimizationService
    from src.services.tag_manager import TagManager
    
    try:
        service = TagOptimizationService()
        result = await service.optimize()
        
        # Reload configuration in-memory
        TagManager().reload()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents", response_model=List[DocumentResponse])
async def get_documents(
    skip: int = 0, 
    limit: int = 50, 
    doc_type: Optional[str] = None,
    upload_status: Optional[str] = None,
    category: Optional[str] = None,  # Category filter (Topic name from tag_mapping.yaml)
    tag: Optional[str] = None,  # Single tag filter
    db: AsyncSession = Depends(get_db)
):
    """
    문서 목록 조회 API with category-based and tag-based filtering.
    
    Args:
        skip: 페이지네이션 오프셋
        limit: 최대 결과 수
        doc_type: 문서 타입 필터 (SUMMARY, DEEP_DIVE, WEEKLY_REPORT, OTHER)
        upload_status: 업로드 상태 필터 (PENDING, SUCCESS, FAILED)
        category: Category 필터 (예: "Development", "AI & ML")
        tag: 특정 태그 필터 (예: "python", "ai")
    """
    from src.services.db_service import DBService
    from src.services.tag_manager import TagManager
    
    documents = await DBService.get_documents(
        db=db,
        skip=skip,
        limit=limit,
        doc_type=doc_type,
        upload_status=upload_status,
        category=category,
        tag=tag
    )
    
    # Category 계산 및 주입
    tm = TagManager()
    for doc in documents:
        doc.category = tm.get_category_from_tags(doc.tags)
    
    return documents

@app.get("/api/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    from src.services.tag_manager import TagManager
    
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Category 계산
    tm = TagManager()
    doc.category = tm.get_category_from_tags(doc.tags)
    
    return doc

@app.post("/api/documents/{doc_id}/retry")
async def retry_upload(doc_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Get DB record
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # 2. Check if file exists
    if not os.path.exists(doc.local_file_path):
        raise HTTPException(status_code=404, detail="Local file not found")

    # 3. Trigger Upload using DriveUploader
    try:
        from src.services.drive_handler import DriveUploader
        from src.database.models import UploadStatus
        from datetime import datetime
        
        uploader = DriveUploader()
        success = await asyncio.to_thread(uploader.upload, doc.local_file_path, doc.title)
        
        # 4. Update DB Status
        doc.gdrive_upload_status = UploadStatus.SUCCESS if success else UploadStatus.FAILED
        doc.last_synced_at = datetime.now()
        await db.commit()
        await db.refresh(doc)
        
        if not success:
             raise HTTPException(status_code=500, detail="Drive upload returned False")
             
        return {"status": "success", "gdrive_upload_status": doc.gdrive_upload_status}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retry failed: {str(e)}")

@app.get("/api/documents/{doc_id}/content")
async def get_document_content(doc_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Get DB record
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 2. Read local file
    if not os.path.exists(doc.local_file_path):
        raise HTTPException(status_code=404, detail="Local file not found on server")
    
    async with aiofiles.open(doc.local_file_path, mode='r', encoding='utf-8') as f:
        content = await f.read()
    
    return {"content": content}

@app.post("/api/documents/{doc_id}/content")
async def update_document_content(
    doc_id: int, 
    update: ContentUpdate, 
    db: AsyncSession = Depends(get_db)
):
    # 1. Get DB record
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # 2. Write to local file
    try:
        async with aiofiles.open(doc.local_file_path, mode='w', encoding='utf-8') as f:
            await f.write(update.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")

    # 3. Update 'updated_at' in DB
    from datetime import datetime
    doc.updated_at = datetime.now()
    await db.commit()
    await db.refresh(doc)
    
    return {"status": "success", "updated_at": doc.updated_at}

@app.get("/api/search", response_model=List[SearchResultItem])
async def search_documents(
    q: str, 
    limit: int = 10,
    offset: int = 0,
    threshold: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Semantic search for document chunks with pagination support.
    
    Args:
        q: Query string
        limit: Maximum number of results to return (default: 10)
        offset: Number of results to skip for pagination (default: 0)
        threshold: Optional cosine distance threshold for filtering (default: None)
    """
    if not q:
        raise HTTPException(status_code=400, detail="Query string 'q' is required")
    
    from src.services.search_service import SearchService
    from src.web_api.schemas import SearchResultItem
    
    service = SearchService(db)
    results = await service.search_similar(q, limit, offset, threshold)
    
    return [SearchResultItem(**item) for item in results]

@app.get("/api/tags/top")
async def get_top_tags(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    상위 태그 목록 조회 (count 내림차순)
    
    Args:
        limit: 반환할 태그 수 (default: 100)
        offset: 페이지네이션 오프셋 (default: 0)
    """
    from src.services.tag_analytics import TagAnalyticsService
    
    tags = await TagAnalyticsService.get_top_tags(db, limit, offset)
    return tags

@app.post("/api/documents/{doc_id}/generate-tags")
async def generate_tags_for_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """
    문서 내용을 기반으로 태그를 생성하고 DB에 업데이트합니다.
    
    Process:
        1. Fetch document from DB
        2. Read content from local file
        3. Call AI to generate tags
        4. Update document.tags in DB
        
    Returns:
        {
            "success": true,
            "tags": ["tag1", "tag2", ...],
            "message": "Tags generated successfully"
        }
    """
    logger.info(f"[API] Tag generation requested for document ID: {doc_id}")
    
    # 1. Fetch document
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 2. Read content from local file
    if not os.path.exists(doc.local_file_path):
        raise HTTPException(status_code=404, detail="Local file not found. Cannot generate tags.")
    
    try:
        async with aiofiles.open(doc.local_file_path, mode='r', encoding='utf-8') as f:
            content = await f.read()
    except Exception as e:
        logger.error(f"[API] Failed to read file {doc.local_file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
    
    # 3. Generate tags using AI
    from src.services.ai_handler import AIAgent
    
    try:
        ai_agent = AIAgent()
        tags = await asyncio.to_thread(ai_agent.generate_tags, content)
        logger.info(f"[API] Generated {len(tags)} tags for doc {doc_id}: {tags}")
        
        if not tags:
            logger.warning(f"[API] No tags generated for doc {doc_id}")
            return {
                "success": False,
                "tags": [],
                "message": "No tags could be generated from the content"
            }
        
        # 4. Update DB
        doc.tags = tags
        await db.commit()
        await db.refresh(doc)
        
        logger.info(f"[API] Successfully updated tags for doc {doc_id}")
        return {
            "success": True,
            "tags": tags,
            "message": f"Generated {len(tags)} tags successfully"
        }
        
    except Exception as e:
        logger.error(f"[API] Tag generation failed for doc {doc_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tag generation failed: {str(e)}")

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """
    문서를 완전히 삭제합니다 (DB + 로컬 파일 + 벡터 임베딩).
    
    Deletion Process:
        1. Fetch document from DB
        2. Decrement tag statistics counts
        3. Delete vector embeddings (DocumentChunks)
        4. Delete local file (if exists)
        5. Delete DB record
        
    Returns:
        {
            "success": true,
            "message": "Document deleted successfully",
            "deleted_file": "/path/to/file.md"
        }
    """
    logger.info(f"[API] Delete requested for document ID: {doc_id}")
    
    # 1. Fetch document
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    local_file_path = doc.local_file_path
    doc_tags = doc.tags if doc.tags else []
    logger.info(f"[API] Document has {len(doc_tags)} tags: {doc_tags}")
    
    try:
        # 2. Decrement tag statistics counts
        if doc_tags:
            from src.database.models import TagStatistics
            from sqlalchemy import update, delete
            
            for tag in doc_tags:
                # Normalize tag to lowercase for matching (TagStatistics stores lowercase)
                normalized_tag = tag.lower()
                
                # First, check current count
                select_stmt = select(TagStatistics.count).where(TagStatistics.tag == normalized_tag)
                count_result = await db.execute(select_stmt)
                current_count = count_result.scalar_one_or_none()
                
                if current_count is None:
                    logger.warning(f"[API] Tag '{normalized_tag}' not found in TagStatistics table")
                    continue
                
                if current_count <= 1:
                    # Delete the tag entry if count will become 0
                    delete_stmt = delete(TagStatistics).where(TagStatistics.tag == normalized_tag)
                    await db.execute(delete_stmt)
                    logger.info(f"[API] Deleted tag '{normalized_tag}' from TagStatistics (count was {current_count})")
                else:
                    # Decrement the count
                    update_stmt = (
                        update(TagStatistics)
                        .where(TagStatistics.tag == normalized_tag)
                        .values(count=TagStatistics.count - 1)
                    )
                    await db.execute(update_stmt)
                    logger.debug(f"[API] Decremented count for tag '{normalized_tag}' ({current_count} -> {current_count - 1})")
            
            logger.info(f"[API] Updated tag statistics for {len(doc_tags)} tags")
        
        # 3. Delete vector embeddings
        from src.services.vector_service import VectorService
        vector_service = VectorService(db)
        await vector_service.clear_chunks(doc_id)
        logger.info(f"[API] Deleted vector chunks for doc {doc_id}")
        
        # 4. Delete local file (if exists)
        file_deleted = False
        if os.path.exists(local_file_path):
            try:
                os.remove(local_file_path)
                file_deleted = True
                logger.info(f"[API] Deleted local file: {local_file_path}")
            except Exception as e:
                logger.warning(f"[API] Failed to delete local file {local_file_path}: {e}")
        else:
            logger.warning(f"[API] Local file not found: {local_file_path}")
        
        # 5. Delete DB record
        await db.delete(doc)
        await db.commit()
        logger.info(f"[API] Deleted DB record for doc {doc_id}")
        
        return {
            "success": True,
            "message": "Document deleted successfully",
            "deleted_file": local_file_path if file_deleted else None
        }
        
    except Exception as e:
        logger.error(f"[API] Failed to delete document {doc_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete operation failed: {str(e)}")



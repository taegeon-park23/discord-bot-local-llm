from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import OperationalError
from sqlalchemy import cast, func
from sqlalchemy.dialects.postgresql import ARRAY
import sqlalchemy as sa
from src.database.models import Document, DocType, UploadStatus
from src.database.engine import AsyncSessionLocal
from src.logger import get_logger
import datetime
import asyncio
from functools import wraps

logger = get_logger(__name__)

def async_retry_on_lock(max_retries=5, base_delay=0.1):
    """SQLite 락 발생 시 재시도하는 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except OperationalError as e:
                    if "locked" in str(e).lower() and attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"[DB] Database locked, retry {attempt+1}/{max_retries} after {delay}s")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"[DB] Operation failed after {max_retries} retries: {e}")
                        raise
            return None
        return wrapper
    return decorator

class DBService:
    @staticmethod
    @async_retry_on_lock(max_retries=5, base_delay=0.1)
    async def register_document(
        title: str,
        local_path: str,
        doc_type: DocType,
        source_url: str = None,
        raw_tags: list = None  # NEW: Optional raw tags from LLM or manual input
    ) -> Document:
        async with AsyncSessionLocal() as db:
            # Check if exists
            result = await db.execute(select(Document).where(Document.local_file_path == local_path))
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.title = title
                existing.updated_at = datetime.datetime.now()
                
                # Update tags if provided
                if raw_tags:
                    from src.services.tag_manager import TagManager
                    tm = TagManager()
                    existing.tags = tm.normalize_tags(raw_tags)
                
                await db.commit()
                await db.refresh(existing)
                return existing
            
            # Infer tags for new document
            inferred_tags = []
            if raw_tags:
                # LLM이 제공한 tags 사용
                from src.services.tag_manager import TagManager
                tm = TagManager()
                inferred_tags = tm.normalize_tags(raw_tags)
            else:
                # Tags가 없으면 경로와 제목에서 추론
                inferred_tags = await DBService._infer_tags_for_new_document(local_path, title)
            
            new_doc = Document(
                title=title,
                local_file_path=local_path,
                doc_type=doc_type,
                source_url=source_url,
                tags=inferred_tags,  # Inferred tags 추가
                gdrive_upload_status=UploadStatus.PENDING
            )
            db.add(new_doc)
            await db.commit()
            await db.refresh(new_doc)
            return new_doc

    @staticmethod
    async def _infer_tags_for_new_document(local_path: str, title: str) -> list:
        """
        신규 문서의 tags를 경로와 제목으로부터 추론
        """
        from pathlib import Path
        from src.services.tag_manager import TagManager
        import re
        
        tm = TagManager()
        tags = set()
        
        # 1. 경로에서 폴더명 추출
        FOLDER_TO_TOPIC = {
            "AI & ML": "AI & ML",
            "AI Agent": "AI & ML",
            "Design": "Design",
            "Development": "Development",
            "API": "Development",
            "Custom Hooks": "Development",
            "B-tree": "Development",
            "DevOps & Cloud": "DevOps & Cloud",
            "Data Science": "Data Science",
            "Security": "Security",
        }
        
        try:
            path_obj = Path(local_path)
            if len(path_obj.parts) > 3 and path_obj.parts[1] == "app" and path_obj.parts[2] == "data":
                folder_name = path_obj.parts[3]
                topic = FOLDER_TO_TOPIC.get(folder_name)
                if topic:
                    topic_tags = tm.get_tags_for_category(topic)
                    if topic_tags:
                        tags.update(topic_tags[:2])  # 대표 태그 2개만
        except:
            pass
        
        # 2. 제목에서 키워드 추론
        title_lower = title.lower()
        for group in tm.mappings:
            for synonym in group.get('synonyms', [])[:10]:  # 상위 10개만
                pattern = r'\b' + re.escape(synonym.lower()) + r'\b'
                if re.search(pattern, title_lower):
                    tags.add(synonym.lower())
                    break  # 하나만 매칭되면 다음 그룹으로
        
        # 3. 정규화
        if tags:
            return tm.normalize_tags(list(tags))
        else:
            return []  # 추론 실패 시 빈 리스트


    @staticmethod
    @async_retry_on_lock(max_retries=5, base_delay=0.1)
    async def update_upload_status(
        local_path: str,
        status: UploadStatus,
        gdrive_id: str = None
    ):
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Document).where(Document.local_file_path == local_path))
            doc = result.scalar_one_or_none()
            if doc:
                doc.gdrive_upload_status = status
                if gdrive_id:
                    doc.gdrive_file_id = gdrive_id
                doc.last_synced_at = datetime.datetime.now()
                await db.commit()

    @staticmethod
    def _build_filter_query(
        doc_type: str = None,
        upload_status: str = None,
        category: str = None,
        tag: str = None
    ):
        """Builds the base usage query with filters applied."""
        query = select(Document)
        
        # doc_type 필터
        if doc_type:
            query = query.where(Document.doc_type == doc_type)
        
        # upload_status 필터
        if upload_status:
            query = query.where(Document.gdrive_upload_status == upload_status)
        
        # category 필터 (Tags 기반)
        if category:
            from src.services.tag_manager import TagManager
            tag_manager = TagManager()
            
            if category.lower() == "uncategorized":
                # tags가 없거나 빈 배열인 문서 검색
                query = query.where(
                    sa.or_(
                        Document.tags == None,
                        func.jsonb_array_length(Document.tags) == 0
                    )
                )
            else:
                target_tags = tag_manager.get_tags_for_category(category)
                if target_tags:
                    # PostgreSQL JSONB 배열이 target_tags 중 하나라도 포함하는지 확인
                    query = query.where(
                        func.jsonb_exists_any(Document.tags, cast(target_tags, ARRAY(sa.String)))
                    )
                else:
                    # 유효하지 않은 카테고리인 경우 결과 없음
                    query = query.where(sa.false())
        
        # tag 필터 (단일 태그 검색, 대소문자만 무시, 정확한 매칭)
        if tag:
            # 태그를 소문자로 정규화
            normalized_tag = tag.lower().strip()
            # JSONB 배열의 각 요소를 소문자로 변환하여 정확히 비교 (LIKE가 아닌 == 사용)
            # 예: "tech"는 "Tech", "TECH"와 매칭되지만 "technology"와는 매칭되지 않음
            query = query.where(
                sa.exists(
                    select(1).select_from(
                        func.jsonb_array_elements_text(Document.tags).alias('tag_element')
                    ).where(
                        func.lower(sa.text('tag_element')) == normalized_tag  # 정확한 매칭 (==)
                    )
                )
            )
        
        return query

    @staticmethod
    async def count_documents(
        db: AsyncSession,
        doc_type: str = None,
        upload_status: str = None,
        category: str = None,
        tag: str = None
    ) -> int:
        """Counts documents matching the filters."""
        base_query = DBService._build_filter_query(doc_type, upload_status, category, tag)
        # Wrapping in subquery is safer for complex wheres, but func.count() on selection is standard
        # However, selecting the entity then counting might be less efficient than count(*).
        # Let's use select(func.count()).select_from(base_query.subquery()) or modify base query to select count.
        
        # Resetting selection to count
        # SQLAlchemy 1.4+ style
        count_query = select(func.count()).select_from(base_query.subquery())
        result = await db.execute(count_query)
        return result.scalar() or 0

    @staticmethod
    async def get_documents(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        doc_type: str = None,
        upload_status: str = None,
        category: str = None,
        tag: str = None
    ):
        """
        문서 목록을 필터링 조건에 따라 조회.
        """
        query = DBService._build_filter_query(doc_type, upload_status, category, tag)
        query = query.order_by(Document.created_at.desc(), Document.id.desc())
        
        # Pagination
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import OperationalError
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
        source_url: str = None
    ) -> Document:
        async with AsyncSessionLocal() as db:
            # Check if exists
            result = await db.execute(select(Document).where(Document.local_file_path == local_path))
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.title = title
                existing.updated_at = datetime.datetime.now()
                # document already registered
                await db.commit()
                return existing
            
            new_doc = Document(
                title=title,
                local_file_path=local_path,
                doc_type=doc_type,
                source_url=source_url,
                gdrive_upload_status=UploadStatus.PENDING
            )
            db.add(new_doc)
            await db.commit()
            await db.refresh(new_doc)
            return new_doc

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

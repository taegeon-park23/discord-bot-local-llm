from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.database.models import Document, DocType, UploadStatus
from src.database.engine import AsyncSessionLocal
import datetime

class DBService:
    @staticmethod
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

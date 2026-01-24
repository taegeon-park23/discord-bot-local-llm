from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class DocType(str, Enum):
    SUMMARY = "SUMMARY"
    DEEP_DIVE = "DEEP_DIVE"
    WEEKLY_REPORT = "WEEKLY_REPORT"
    OTHER = "OTHER"

class UploadStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class DocumentBase(BaseModel):
    title: str
    doc_type: DocType
    local_file_path: str

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    gdrive_upload_status: UploadStatus
    gdrive_file_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    tags: list[str] = []
    category: Optional[str] = None

    class Config:
        from_attributes = True

class ContentUpdate(BaseModel):
    content: str

class DashboardStats(BaseModel):
    total_documents: int
    failed_uploads: int
    recent_docs_count: int

class SearchResultItem(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    content: str
    score: Optional[str] = "N/A"

class SearchResponse(BaseModel):
    results: list[SearchResultItem]

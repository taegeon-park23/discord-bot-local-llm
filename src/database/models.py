from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class DocType(str, enum.Enum):
    SUMMARY = "SUMMARY"
    DEEP_DIVE = "DEEP_DIVE"
    WEEKLY_REPORT = "WEEKLY_REPORT"
    OTHER = "OTHER"

class UploadStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    source_url = Column(Text, nullable=True)
    
    doc_type = Column(SAEnum(DocType), default=DocType.SUMMARY, nullable=False)
    
    # Tags for category-based filtering
    tags = Column(JSONB, default=list, server_default='[]', nullable=False)
    
    # Local File Info - Source of Truth
    local_file_path = Column(Text, unique=True, nullable=False)
    
    # Google Drive Info
    gdrive_file_id = Column(String(255), nullable=True)
    gdrive_upload_status = Column(SAEnum(UploadStatus), default=UploadStatus.PENDING, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Document id={self.id} title='{self.title}' status='{self.gdrive_upload_status}'>"

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768))  # Gemini Text Embedding 004 dimension

    document = relationship("Document", backref="chunks")

    def __repr__(self):
        return f"<DocumentChunk id={self.id} doc_id={self.document_id} index={self.chunk_index}>"

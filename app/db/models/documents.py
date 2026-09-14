"""SQLAlchemy ORM models for Document and DocumentVersion."""

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.domain.models.document import DocumentStatus, DocumentVersionStatus
from app.domain.metadata.source import SourceType
import uuid
import datetime


class DocumentORM(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    
    # Source metadata (embedded JSON)
    source_type = Column(SQLEnum(SourceType), nullable=False, default=SourceType.FILESYSTEM.value)
    source_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_extension = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    mime_type = Column(String, nullable=True)
    checksum_sha256 = Column(String(64), nullable=False, unique=True, index=True)
    last_modified = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(SQLEnum(DocumentStatus), nullable=False, default=DocumentStatus.PENDING.value)
    
    # Additional metadata
    metadata_ = Column("metadata", JSONB, nullable=False, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationship
    versions = relationship("DocumentVersionORM", back_populates="document", cascade="all, delete-orphan", order_by="DocumentVersionORM.version_number")

    def __repr__(self):
        return f"<DocumentORM(id={self.id}, title='{self.title}', status='{self.status}')>"


class DocumentVersionORM(Base):
    __tablename__ = "document_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    content_hash = Column(String(64), nullable=False)
    status = Column(SQLEnum(DocumentVersionStatus), nullable=False, default=DocumentVersionStatus.ACTIVE.value)
    chunk_count = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    
    # Source metadata snapshot at version creation
    source_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_extension = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    mime_type = Column(String, nullable=True)
    checksum_sha256 = Column(String(64), nullable=False)
    last_modified = Column(DateTime(timezone=True), nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    document = relationship("DocumentORM", back_populates="versions")

    def __repr__(self):
        return f"<DocumentVersionORM(id={self.id}, document_id={self.document_id}, v{self.version_number})>"
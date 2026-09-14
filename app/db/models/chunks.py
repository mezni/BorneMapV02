"""SQLAlchemy ORM model for Chunk."""

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.domain.models.chunk import ChunkType
import uuid


class ChunkORM(Base):
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    document_version_id = Column(UUID(as_uuid=True), ForeignKey("document_versions.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False, default=0)
    chunk_type = Column(SQLEnum(ChunkType), nullable=False, default=ChunkType.PARENT.value)
    parent_chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id"), nullable=True)

    # Content
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False, default=0)
    char_count = Column(Integer, nullable=False, default=0)
    embedding = Column(JSONB, nullable=True)

    # Additional metadata
    metadata_ = Column("metadata", JSONB, nullable=False, default={})

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    # Relationships
    document = relationship("DocumentORM")
    document_version = relationship("DocumentVersionORM")

    def __repr__(self):
        return f"<ChunkORM(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index}, type='{self.chunk_type}')>"
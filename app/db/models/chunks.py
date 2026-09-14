"""SQLAlchemy ORM model for Chunk."""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.config import load_runtime_config
from app.db.session import Base
from app.domain.models.chunk import ChunkType


_VECTOR_DIMS = load_runtime_config().database.vector_index.dims


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
    embedding = Column(Vector(_VECTOR_DIMS), nullable=True)

    # Additional metadata
    metadata_ = Column("metadata", JSONB, nullable=False, default={})

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    # Relationships
    document = relationship("DocumentORM")
    document_version = relationship("DocumentVersionORM")

    def __repr__(self):
        return f"<ChunkORM(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index}, type='{self.chunk_type}')>"
"""Core domain entity for Document."""

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID, uuid4

from app.domain.metadata.source import SourceMetadata, SourceType


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # Deduplicated


class DocumentVersionStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class DocumentVersion(BaseModel):
    """Represents a version of a document."""
    
    model_config = ConfigDict(extra="forbid")
    
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID = Field(default_factory=uuid4)
    version_number: int = 1
    source_metadata: Optional[SourceMetadata] = None
    content_hash: str = ""
    status: DocumentVersionStatus = DocumentVersionStatus.ACTIVE
    chunk_count: int = 0
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "version_number": self.version_number,
            "source_metadata": self.source_metadata.to_dict() if self.source_metadata else None,
            "content_hash": self.content_hash,
            "status": self.status.value,
            "chunk_count": self.chunk_count,
            "total_tokens": self.total_tokens,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error_message": self.error_message,
        }


class Document(BaseModel):
    """Core domain entity representing a document to be indexed."""
    
    model_config = ConfigDict(extra="forbid")
    
    id: UUID = Field(default_factory=uuid4)
    title: str = ""
    source_metadata: Optional[SourceMetadata] = None
    versions: List[DocumentVersion] = Field(default_factory=list)
    status: DocumentStatus = DocumentStatus.PENDING
    current_version: Optional[DocumentVersion] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_version(self, version: DocumentVersion) -> None:
        """Add a new version, marking previous as superseded."""
        if self.current_version:
            self.current_version.status = DocumentVersionStatus.SUPERSEDED
        version.document_id = self.id
        version.version_number = len(self.versions) + 1
        self.versions.append(version)
        self.current_version = version
        self.status = DocumentStatus.PROCESSING
        self.updated_at = datetime.utcnow()
    
    def mark_completed(self) -> None:
        """Mark document as fully processed."""
        self.status = DocumentStatus.COMPLETED
        if self.current_version:
            self.current_version.status = DocumentVersionStatus.ACTIVE
            self.current_version.processed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_failed(self, error: str) -> None:
        """Mark document as failed."""
        self.status = DocumentStatus.FAILED
        if self.current_version:
            self.current_version.status = DocumentVersionStatus.ACTIVE
            self.current_version.error_message = error
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "title": self.title,
            "source_metadata": self.source_metadata.to_dict() if self.source_metadata else None,
            "versions": [v.to_dict() for v in self.versions],
            "status": self.status.value,
            "current_version_id": str(self.current_version.id) if self.current_version else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
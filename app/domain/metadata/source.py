"""Source metadata for document ingestion tracking."""

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from uuid import UUID, uuid4


class SourceType(str, Enum):
    FILESYSTEM = "filesystem"
    API = "api"
    DATABASE = "database"
    WEBHOOK = "webhook"


class SourceMetadata(BaseModel):
    """Metadata about the source of a document."""
    
    model_config = ConfigDict(extra="forbid")
    
    id: UUID = Field(default_factory=uuid4)
    source_type: SourceType = SourceType.FILESYSTEM
    source_path: str = ""
    file_name: str = ""
    file_extension: str = ""
    file_size_bytes: int = 0
    mime_type: Optional[str] = None
    checksum_sha256: Optional[str] = None
    last_modified: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    additional_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "source_type": self.source_type.value,
            "source_path": self.source_path,
            "file_name": self.file_name,
            "file_extension": self.file_extension,
            "file_size_bytes": self.file_size_bytes,
            "mime_type": self.mime_type,
            "checksum_sha256": self.checksum_sha256,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "created_at": self.created_at.isoformat(),
            "additional_metadata": self.additional_metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceMetadata":
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            source_type=SourceType(data.get("source_type", "filesystem")),
            source_path=data.get("source_path", ""),
            file_name=data.get("file_name", ""),
            file_extension=data.get("file_extension", ""),
            file_size_bytes=data.get("file_size_bytes", 0),
            mime_type=data.get("mime_type"),
            checksum_sha256=data.get("checksum_sha256"),
            last_modified=datetime.fromisoformat(data["last_modified"]) if data.get("last_modified") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            additional_metadata=data.get("additional_metadata", {}),
        )
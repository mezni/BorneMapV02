"""Core domain entity for Chunk."""

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID, uuid4


class ChunkType(str, Enum):
    PARENT = "parent"
    CHILD = "child"


class Chunk(BaseModel):
    """A chunk of a document version, ready for embedding and retrieval."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID = Field(default_factory=uuid4)
    document_version_id: UUID = Field(default_factory=uuid4)
    chunk_index: int = 0
    chunk_type: ChunkType = ChunkType.PARENT
    parent_chunk_id: Optional[UUID] = None
    content: str = ""
    token_count: int = 0
    char_count: int = 0
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "document_version_id": str(self.document_version_id),
            "chunk_index": self.chunk_index,
            "chunk_type": self.chunk_type.value,
            "parent_chunk_id": str(self.parent_chunk_id) if self.parent_chunk_id else None,
            "content": self.content,
            "token_count": self.token_count,
            "char_count": self.char_count,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }
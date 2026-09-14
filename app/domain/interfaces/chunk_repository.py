"""Repository interface for Chunk."""

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from app.domain.models.chunk import Chunk


class AbstractChunkRepository(ABC):
    @abstractmethod
    def add(self, chunk: Chunk) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_many(self, chunks: List[Chunk]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, chunk_id: UUID) -> Optional[Chunk]:
        raise NotImplementedError

    @abstractmethod
    def list_by_document(self, document_id: UUID) -> List[Chunk]:
        raise NotImplementedError

    @abstractmethod
    def list_by_version(self, document_version_id: UUID) -> List[Chunk]:
        raise NotImplementedError

    @abstractmethod
    def count_by_version(self, document_version_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    def delete(self, chunk_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_by_document(self, document_id: UUID) -> None:
        raise NotImplementedError
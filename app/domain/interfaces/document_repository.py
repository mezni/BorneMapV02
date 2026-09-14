"""Repository interfaces for Document and DocumentVersion."""

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from app.domain.models.document import Document, DocumentVersion


class AbstractDocumentRepository(ABC):
    @abstractmethod
    def add(self, document: Document) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, document_id: UUID) -> Optional[Document]:
        raise NotImplementedError

    @abstractmethod
    def get_by_checksum(self, checksum: str) -> Optional[Document]:
        raise NotImplementedError

    @abstractmethod
    def update(self, document: Document) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, document_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    def list(self, skip: int = 0, limit: int = 100) -> List[Document]:
        raise NotImplementedError


class AbstractDocumentVersionRepository(ABC):
    @abstractmethod
    def add(self, version: DocumentVersion) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, version_id: UUID) -> Optional[DocumentVersion]:
        raise NotImplementedError

    @abstractmethod
    def list_by_document(self, document_id: UUID) -> List[DocumentVersion]:
        raise NotImplementedError
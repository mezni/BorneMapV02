"""SQLAlchemy implementation of Document and DocumentVersion repositories."""

from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.db.models.documents import DocumentORM, DocumentVersionORM
from app.domain.models.document import Document, DocumentVersion, DocumentStatus, DocumentVersionStatus
from app.domain.metadata.source import SourceMetadata, SourceType
from app.domain.interfaces.document_repository import AbstractDocumentRepository, AbstractDocumentVersionRepository


class SQLAlchemyDocumentRepository(AbstractDocumentRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_domain_model(self, doc_orm: DocumentORM) -> Document:
        source_metadata = SourceMetadata(
            id=doc_orm.id,
            source_type=SourceType(doc_orm.source_type) if isinstance(doc_orm.source_type, str) else doc_orm.source_type,
            source_path=doc_orm.source_path,
            file_name=doc_orm.file_name,
            file_extension=doc_orm.file_extension,
            file_size_bytes=doc_orm.file_size_bytes,
            mime_type=doc_orm.mime_type,
            checksum_sha256=doc_orm.checksum_sha256,
            last_modified=doc_orm.last_modified,
            created_at=doc_orm.created_at,
            additional_metadata=doc_orm.metadata_,
        )

        versions = []
        for v_orm in doc_orm.versions:
            version = DocumentVersion(
                id=v_orm.id,
                document_id=v_orm.document_id,
                version_number=v_orm.version_number,
                content_hash=v_orm.content_hash,
                status=DocumentVersionStatus(v_orm.status) if isinstance(v_orm.status, str) else v_orm.status,
                chunk_count=v_orm.chunk_count,
                total_tokens=v_orm.total_tokens,
                created_at=v_orm.created_at,
                processed_at=v_orm.processed_at,
                error_message=v_orm.error_message,
            )
            versions.append(version)

        current_version = None
        if versions:
            current_version = versions[-1]

        return Document(
            id=doc_orm.id,
            title=doc_orm.title,
            source_metadata=source_metadata,
            versions=versions,
            status=DocumentStatus(doc_orm.status) if isinstance(doc_orm.status, str) else doc_orm.status,
            current_version=current_version,
            created_at=doc_orm.created_at,
            updated_at=doc_orm.updated_at,
            metadata=doc_orm.metadata_,
        )

    def _to_orm_model(self, document: Document) -> DocumentORM:
        source_meta = document.source_metadata
        
        # Get or create versions
        versions_orm = []
        for v in document.versions:
            v_meta = v.source_metadata or source_meta
            versions_orm.append(DocumentVersionORM(
                id=v.id,
                document_id=document.id,
                version_number=v.version_number,
                content_hash=v.content_hash,
                status=v.status.value if isinstance(v.status, DocumentVersionStatus) else v.status,
                chunk_count=v.chunk_count,
                total_tokens=v.total_tokens,
                source_path=v_meta.source_path if v_meta else source_meta.source_path if source_meta else "",
                file_name=v_meta.file_name if v_meta else source_meta.file_name if source_meta else "",
                file_extension=v_meta.file_extension if v_meta else source_meta.file_extension if source_meta else "",
                file_size_bytes=v_meta.file_size_bytes if v_meta else source_meta.file_size_bytes if source_meta else 0,
                mime_type=v_meta.mime_type if v_meta else source_meta.mime_type if source_meta else None,
                checksum_sha256=v_meta.checksum_sha256 if v_meta else source_meta.checksum_sha256 if source_meta else "",
                last_modified=v_meta.last_modified if v_meta else source_meta.last_modified if source_meta else None,
                created_at=v.created_at,
                processed_at=v.processed_at,
                error_message=v.error_message,
            ))

        return DocumentORM(
            id=document.id,
            title=document.title,
            source_type=source_meta.source_type.value if source_meta else SourceType.FILESYSTEM.value,
            source_path=source_meta.source_path if source_meta else "",
            file_name=source_meta.file_name if source_meta else "",
            file_extension=source_meta.file_extension if source_meta else "",
            file_size_bytes=source_meta.file_size_bytes if source_meta else 0,
            mime_type=source_meta.mime_type if source_meta else None,
            checksum_sha256=source_meta.checksum_sha256 if source_meta else "",
            last_modified=source_meta.last_modified if source_meta else None,
            status=document.status.value if isinstance(document.status, DocumentStatus) else document.status,
            metadata_=document.metadata,
            created_at=document.created_at,
            updated_at=document.updated_at,
            versions=versions_orm,
        )

    def add(self, document: Document) -> None:
        doc_orm = self._to_orm_model(document)
        self.session.add(doc_orm)

    def get(self, document_id: UUID) -> Optional[Document]:
        doc_orm = self.session.query(DocumentORM).filter_by(id=document_id).first()
        if doc_orm:
            return self._to_domain_model(doc_orm)
        return None

    def get_by_checksum(self, checksum: str) -> Optional[Document]:
        doc_orm = self.session.query(DocumentORM).filter_by(checksum_sha256=checksum).first()
        if doc_orm:
            return self._to_domain_model(doc_orm)
        return None

    def update(self, document: Document) -> None:
        doc_orm = self.session.query(DocumentORM).filter_by(id=document.id).first()
        if doc_orm:
            source_meta = document.source_metadata
            doc_orm.title = document.title
            doc_orm.source_type = source_meta.source_type.value if source_meta else SourceType.FILESYSTEM.value
            doc_orm.source_path = source_meta.source_path if source_meta else ""
            doc_orm.file_name = source_meta.file_name if source_meta else ""
            doc_orm.file_extension = source_meta.file_extension if source_meta else ""
            doc_orm.file_size_bytes = source_meta.file_size_bytes if source_meta else 0
            doc_orm.mime_type = source_meta.mime_type if source_meta else None
            doc_orm.checksum_sha256 = source_meta.checksum_sha256 if source_meta else ""
            doc_orm.last_modified = source_meta.last_modified if source_meta else None
            doc_orm.status = document.status.value if isinstance(document.status, DocumentStatus) else document.status
            doc_orm.metadata_ = document.metadata
            doc_orm.updated_at = document.updated_at
            
            # Update versions - delete old and add new
            for v_orm in doc_orm.versions:
                self.session.delete(v_orm)
            
            versions_orm = []
            for v in document.versions:
                v_meta = v.source_metadata or source_meta
                versions_orm.append(DocumentVersionORM(
                    id=v.id,
                    document_id=document.id,
                    version_number=v.version_number,
                    content_hash=v.content_hash,
                    status=v.status.value if isinstance(v.status, DocumentVersionStatus) else v.status,
                    chunk_count=v.chunk_count,
                    total_tokens=v.total_tokens,
                    source_path=v_meta.source_path if v_meta else source_meta.source_path if source_meta else "",
                    file_name=v_meta.file_name if v_meta else source_meta.file_name if source_meta else "",
                    file_extension=v_meta.file_extension if v_meta else source_meta.file_extension if source_meta else "",
                    file_size_bytes=v_meta.file_size_bytes if v_meta else source_meta.file_size_bytes if source_meta else 0,
                    mime_type=v_meta.mime_type if v_meta else source_meta.mime_type if source_meta else None,
                    checksum_sha256=v_meta.checksum_sha256 if v_meta else source_meta.checksum_sha256 if source_meta else "",
                    last_modified=v_meta.last_modified if v_meta else source_meta.last_modified if source_meta else None,
                    created_at=v.created_at,
                    processed_at=v.processed_at,
                    error_message=v.error_message,
                ))
            doc_orm.versions = versions_orm
            
            self.session.flush()

    def delete(self, document_id: UUID) -> None:
        doc_orm = self.session.query(DocumentORM).filter_by(id=document_id).first()
        if doc_orm:
            self.session.delete(doc_orm)

    def list(self, skip: int = 0, limit: int = 100) -> List[Document]:
        docs_orm = self.session.query(DocumentORM).order_by(DocumentORM.created_at.desc()).offset(skip).limit(limit).all()
        return [self._to_domain_model(d) for d in docs_orm]


class SQLAlchemyDocumentVersionRepository(AbstractDocumentVersionRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, version: DocumentVersion) -> None:
        # This is handled by the Document repository via cascade
        pass

    def get(self, version_id: UUID) -> Optional[DocumentVersion]:
        v_orm = self.session.query(DocumentVersionORM).filter_by(id=version_id).first()
        if v_orm:
            return self._to_domain_model(v_orm)
        return None

    def list_by_document(self, document_id: UUID) -> List[DocumentVersion]:
        versions_orm = self.session.query(DocumentVersionORM).filter_by(document_id=document_id).order_by(DocumentVersionORM.version_number).all()
        return [self._to_domain_model(v) for v in versions_orm]

    def _to_domain_model(self, v_orm: DocumentVersionORM) -> DocumentVersion:
        return DocumentVersion(
            id=v_orm.id,
            document_id=v_orm.document_id,
            version_number=v_orm.version_number,
            content_hash=v_orm.content_hash,
            status=DocumentVersionStatus(v_orm.status) if isinstance(v_orm.status, str) else v_orm.status,
            chunk_count=v_orm.chunk_count,
            total_tokens=v_orm.total_tokens,
            created_at=v_orm.created_at,
            processed_at=v_orm.processed_at,
            error_message=v_orm.error_message,
        )
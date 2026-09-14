"""SQLAlchemy implementation of the Chunk repository."""

from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.db.models.chunks import ChunkORM
from app.domain.models.chunk import Chunk, ChunkType
from app.domain.interfaces.chunk_repository import AbstractChunkRepository


class SQLAlchemyChunkRepository(AbstractChunkRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_orm_model(self, chunk: Chunk) -> ChunkORM:
        return ChunkORM(
            id=chunk.id,
            document_id=chunk.document_id,
            document_version_id=chunk.document_version_id,
            chunk_index=chunk.chunk_index,
            chunk_type=chunk.chunk_type.value if isinstance(chunk.chunk_type, ChunkType) else chunk.chunk_type,
            parent_chunk_id=chunk.parent_chunk_id,
            content=chunk.content,
            token_count=chunk.token_count,
            char_count=chunk.char_count,
            embedding=chunk.embedding,
            metadata_=chunk.metadata,
            created_at=chunk.created_at,
        )

    def _to_domain_model(self, chunk_orm: ChunkORM) -> Chunk:
        return Chunk(
            id=chunk_orm.id,
            document_id=chunk_orm.document_id,
            document_version_id=chunk_orm.document_version_id,
            chunk_index=chunk_orm.chunk_index,
            chunk_type=ChunkType(chunk_orm.chunk_type) if isinstance(chunk_orm.chunk_type, str) else chunk_orm.chunk_type,
            parent_chunk_id=chunk_orm.parent_chunk_id,
            content=chunk_orm.content,
            token_count=chunk_orm.token_count,
            char_count=chunk_orm.char_count,
            embedding=chunk_orm.embedding,
            metadata=chunk_orm.metadata_,
            created_at=chunk_orm.created_at,
        )

    def add(self, chunk: Chunk) -> None:
        self.session.add(self._to_orm_model(chunk))

    def add_many(self, chunks: List[Chunk]) -> None:
        self.session.add_all([self._to_orm_model(c) for c in chunks])

    def get(self, chunk_id: UUID) -> Optional[Chunk]:
        chunk_orm = self.session.query(ChunkORM).filter_by(id=chunk_id).first()
        if chunk_orm:
            return self._to_domain_model(chunk_orm)
        return None

    def list_by_document(self, document_id: UUID) -> List[Chunk]:
        chunks_orm = (
            self.session.query(ChunkORM)
            .filter_by(document_id=document_id)
            .order_by(ChunkORM.chunk_index)
            .all()
        )
        return [self._to_domain_model(c) for c in chunks_orm]

    def list_by_version(self, document_version_id: UUID) -> List[Chunk]:
        chunks_orm = (
            self.session.query(ChunkORM)
            .filter_by(document_version_id=document_version_id)
            .order_by(ChunkORM.chunk_index)
            .all()
        )
        return [self._to_domain_model(c) for c in chunks_orm]

    def count_by_version(self, document_version_id: UUID) -> int:
        return (
            self.session.query(ChunkORM)
            .filter_by(document_version_id=document_version_id)
            .count()
        )

    def delete(self, chunk_id: UUID) -> None:
        chunk_orm = self.session.query(ChunkORM).filter_by(id=chunk_id).first()
        if chunk_orm:
            self.session.delete(chunk_orm)

    def delete_by_document(self, document_id: UUID) -> None:
        chunks_orm = self.session.query(ChunkORM).filter_by(document_id=document_id).all()
        for chunk_orm in chunks_orm:
            self.session.delete(chunk_orm)
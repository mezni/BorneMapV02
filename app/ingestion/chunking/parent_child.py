"""Parent-child chunker with linked chunk hierarchies."""

from __future__ import annotations

from uuid import UUID

from app.core.config import ParentChildChunking
from app.domain.models.chunk import Chunk, ChunkType
from app.ingestion.chunking.base import BaseChunker
from app.ingestion.chunking.recursive import RecursiveChunker


class ParentChildChunker(BaseChunker):
    """Produces PARENT chunks (broad context) and CHILD chunks (focused detail).

    Children are linked to their containing parent via ``parent_chunk_id`` using
    character offsets recorded on each chunk.
    """

    chunk_type = ChunkType.PARENT

    def __init__(self, config: ParentChildChunking | None = None):
        parent_size = config.parent_chunk_size if config else 1536
        child_size = config.child_chunk_size if config else 512
        child_overlap = config.child_chunk_overlap if config else 64
        self._parent_chunker = RecursiveChunker(chunk_size=parent_size, chunk_overlap=0)
        self._child_chunker = RecursiveChunker(chunk_size=child_size, chunk_overlap=child_overlap)

    def _chunk(self, text: str, document_id: UUID, document_version_id: UUID) -> list[Chunk]:
        parents = self._parent_chunker.chunk_text(text, document_id, document_version_id)
        if not parents:
            return []

        children = self._child_chunker.chunk_text(text, document_id, document_version_id)

        # Attach each child to the parent whose span contains it.
        for child in children:
            child.chunk_type = ChunkType.CHILD
            child_start = _chunk_start(child)
            parent = _parent_for_offset(parents, child_start)
            if parent is not None:
                child.parent_chunk_id = parent.id

        return parents + children


def _chunk_start(chunk: Chunk) -> int:
    start = chunk.metadata.get("start_char")
    return start if isinstance(start, int) else 0


def _parent_for_offset(parents: list[Chunk], offset: int) -> Chunk | None:
    """Return the parent chunk whose [start, end) span contains ``offset``."""
    if offset < 0:
        return None
    for parent in parents:
        start = _chunk_start(parent)
        end_value = parent.metadata.get("end_char")
        end = end_value if isinstance(end_value, int) else start
        if start <= offset < end:
            return parent
    return None

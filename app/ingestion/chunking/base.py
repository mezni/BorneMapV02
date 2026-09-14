"""Base chunker contract, shared helpers, and chunker factory."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from uuid import UUID

from app.core.config import ChunkingConfig
from app.domain.models.chunk import Chunk, ChunkType

_TOKEN_CHARS = 4.0
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE = re.compile(r"\s+")
_PARAGRAPH_BOUNDARY = re.compile(r"\n\s*\n")


def estimate_tokens(text: str) -> int:
    """Best-effort token-count estimate (~4 chars per token)."""
    return max(1, int(len(text) / _TOKEN_CHARS))


def split_sentences(text: str) -> list[str]:
    """Split text into non-empty sentences on . ! ? boundaries."""
    parts = _SENTENCE_BOUNDARY.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def split_paragraphs(text: str) -> list[str]:
    """Split text into non-empty paragraphs on blank-line boundaries."""
    parts = _PARAGRAPH_BOUNDARY.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def _whitespace_tail(text: str, budget_chars: int) -> str:
    """Return up to budget_chars chars from the tail of text, at a word boundary."""
    tail = text[-budget_chars:] if budget_chars > 0 else ""
    head = tail.lstrip()
    if head:
        trimmed = _WHITESPACE.sub(" ", head)
        words = trimmed.split(" ")
        if len(words) > 1:
            return " ".join(words[1:]).strip()
    return tail.strip()


class BaseChunker(ABC):
    """Contract for all text splitters.

    Subclasses implement ``_chunk``; ``chunk_text`` centralises the empty-input
    guard and produces ``Chunk`` entities bound to a document version.
    """

    chunk_type: ChunkType = ChunkType.PARENT

    def chunk_text(
        self,
        text: str,
        document_id: UUID,
        document_version_id: UUID,
    ) -> list[Chunk]:
        """Split ``text`` into ordered chunks for a document version."""
        if text is None or not text.strip():
            return []
        return self._chunk(text, document_id, document_version_id)

    @abstractmethod
    def _chunk(self, text: str, document_id: UUID, document_version_id: UUID) -> list[Chunk]:
        raise NotImplementedError


def get_chunker(config: ChunkingConfig) -> BaseChunker:
    """Instantiate the chunker configured as the active ``chunking.strategy``."""
    if config.strategy == "recursive":
        from app.ingestion.chunking.recursive import RecursiveChunker

        return RecursiveChunker(config.recursive)
    if config.strategy == "token":
        from app.ingestion.chunking.token import TokenChunker

        return TokenChunker(config.token)
    if config.strategy == "semantic":
        from app.ingestion.chunking.semantic import SemanticChunker

        return SemanticChunker(config.semantic)
    if config.strategy == "parent_child":
        from app.ingestion.chunking.parent_child import ParentChildChunker

        return ParentChildChunker(config.parent_child)
    raise ValueError(f"Unknown chunking strategy: {config.strategy}")


# ---------------------------------------------------------------------------
# Embedding contract for semantic chunking
# ---------------------------------------------------------------------------

Embedder = Callable[[list[str]], list[list[float]]]

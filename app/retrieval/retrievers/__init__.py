"""Search engines: pgvector dense similarity, full-text, and hybrid RRF retrieval."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A chunk surfaced by a retriever, with its relevance score."""

    chunk_id: UUID
    document_id: UUID
    document_version_id: UUID
    chunk_index: int
    chunk_type: str
    content: str
    token_count: int
    char_count: int
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


class BaseRetriever(ABC):
    """A retriever ranks chunks for a query and returns :class:`RetrievedChunk` items.

    Subclasses must run within a transaction; :meth:`_txn` reuses the caller's
    active transaction when one exists, otherwise opens and commits its own, so
    statements such as ``SET LOCAL`` stay scoped to the right transaction.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    @contextmanager
    def _txn(self) -> Iterator[None]:
        if self._session.in_transaction():
            yield
        else:
            with self._session.begin():
                yield

    @abstractmethod
    def retrieve(self, query: str, *, top_k: int | None = None) -> list[RetrievedChunk]:
        """Return the top-ranked chunks for ``query``."""
        raise NotImplementedError


from app.retrieval.retrievers.dense import DenseRetriever  # noqa: E402
from app.retrieval.retrievers.hybrid import HybridRetriever  # noqa: E402
from app.retrieval.retrievers.rrf import reciprocal_rank_fusion  # noqa: E402
from app.retrieval.retrievers.sparse import SparseRetriever  # noqa: E402

__all__ = [
    "BaseRetriever",
    "DenseRetriever",
    "HybridRetriever",
    "RetrievedChunk",
    "SparseRetriever",
    "reciprocal_rank_fusion",
]

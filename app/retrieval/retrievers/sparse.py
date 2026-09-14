"""PostgreSQL full-text search retriever (tsvector/tsquery).

Ranks ``chunks`` with ``ts_rank`` against the GIN-indexed generated
``search_vector`` column and the ``websearch_to_tsquery`` query parser,
unleashing PostgreSQL's built-in keyword search without an external index.
"""

from __future__ import annotations

from typing import Any, Mapping
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import SparseRetrievalConfig
from app.retrieval.retrievers import BaseRetriever, RetrievedChunk


class SparseRetriever(BaseRetriever):
    """Rank chunks by PostgreSQL full-text relevance.

    ``language`` selects the regconfig used both by the stored ``search_vector``
    column and by ``websearch_to_tsquery`` (default ``english``, matching the
    ``fulltext`` block of ``configs/database.yaml``).
    """

    def __init__(
        self,
        session: Session,
        config: SparseRetrievalConfig | None = None,
        *,
        language: str = "english",
    ) -> None:
        super().__init__(session)
        self._config = config or SparseRetrievalConfig()
        self._language = language

    def retrieve(self, query: str, *, top_k: int | None = None) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        top_k = top_k or self._config.top_k
        sql = text(
            """
            SELECT
                id, document_id, document_version_id, chunk_index,
                chunk_type::text, content, token_count, char_count, metadata,
                ts_rank(search_vector, websearch_to_tsquery(:language, :query)) AS score
            FROM chunks
            WHERE search_vector @@ websearch_to_tsquery(:language, :query)
            ORDER BY score DESC, chunk_index ASC
            LIMIT :top_k
            """
        )
        with self._txn():
            rows = (
                self._session.execute(
                    sql,
                    {"language": self._language, "query": query, "top_k": top_k},
                )
                .mappings()
                .all()
            )
        return [self._to_retrieved_chunk(row) for row in rows]

    def _to_retrieved_chunk(self, row: Mapping[str, Any]) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id=UUID(str(row["id"])),
            document_id=UUID(str(row["document_id"])),
            document_version_id=UUID(str(row["document_version_id"])),
            chunk_index=int(row["chunk_index"]),
            chunk_type=str(row["chunk_type"]),
            content=str(row["content"]),
            token_count=int(row["token_count"]),
            char_count=int(row["char_count"]),
            metadata=dict(row["metadata"]) if row["metadata"] else {},
            score=float(row["score"]),
        )
"""pgvector dense similarity retriever.

Ranks ``chunks`` by cosine similarity between the query embedding and each
chunk's ``embedding`` vector, returning ``top_k`` results. The HNSW index
(``ix_chunks_embedding_hnsw``) accelerates the ``<=>`` operator; the search
breadth is tuned per query with ``SET LOCAL hnsw.ef_search``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from app.core.config import DenseRetrievalConfig
from app.retrieval.retrievers import BaseRetriever, RetrievedChunk

QueryEmbedder = Callable[[str], Sequence[float]]


class DenseRetriever(BaseRetriever):
    """Rank chunks by cosine similarity to an embedded query.

    The query embedder is injected as a callable (e.g. backed by
    :class:`app.ingestion.embeddings.BaseEmbeddingGenerator`) so this retriever
    stays free of provider dependencies and unit-testable without a network.
    """

    def __init__(
        self,
        session: Session,
        embed_query: QueryEmbedder,
        config: DenseRetrievalConfig | None = None,
    ) -> None:
        super().__init__(session)
        self._embed_query = embed_query
        self._config = config or DenseRetrievalConfig()

    def retrieve(self, query: str, *, top_k: int | None = None) -> list[RetrievedChunk]:
        query_vector = self._embed_query(query)
        if not query_vector:
            return []
        top_k = top_k or self._config.top_k
        qvec = self._format_vector(query_vector)
        sql = text(
            """
            SELECT
                id, document_id, document_version_id, chunk_index,
                chunk_type::text, content, token_count, char_count, metadata,
                1 - (embedding <=> CAST(:qvec AS vector)) AS score
            FROM chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:qvec AS vector)
            LIMIT :top_k
            """
        )
        with self._txn():
            self._session.execute(
                text("SET LOCAL hnsw.ef_search = :ef_search"),
                {"ef_search": self._config.ef_search},
            )
            rows = self._session.execute(sql, {"qvec": qvec, "top_k": top_k}).mappings().all()
        return [self._to_retrieved_chunk(row) for row in rows]

    def _format_vector(self, vector: Sequence[float]) -> str:
        """Render a float sequence as a pgvector literal (``[0.1,0.2,...]``)."""
        return "[" + ",".join(str(float(value)) for value in vector) + "]"

    def _to_retrieved_chunk(self, row: RowMapping) -> RetrievedChunk:
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

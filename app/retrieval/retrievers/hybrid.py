"""Unified dense + sparse execution engine.

Runs the dense and sparse retrievers against the same query, merges their
candidate sets with Reciprocal Rank Fusion, and yields a combined ranking.
"""

from __future__ import annotations

from dataclasses import replace

from sqlalchemy.orm import Session

from app.core.config import HybridRetrievalConfig
from app.retrieval.retrievers import BaseRetriever, RetrievedChunk
from app.retrieval.retrievers.dense import DenseRetriever
from app.retrieval.retrievers.rrf import reciprocal_rank_fusion
from app.retrieval.retrievers.sparse import SparseRetriever


class HybridRetriever(BaseRetriever):
    """Coordinate dense and sparse search and fuse their rankings with RRF.

    Each search engine returns its top ``candidate_k`` chunks; the two results
    are merged by chunk id with :func:`reciprocal_rank_fusion` (weighted by the
    configured dense/sparse weights), de-duplicating any overlap. The fused
    ranking is trimmed to ``top_k`` (default: ``candidate_k``).
    """

    def __init__(
        self,
        session: Session,
        *,
        dense: DenseRetriever,
        sparse: SparseRetriever,
        config: HybridRetrievalConfig | None = None,
    ) -> None:
        super().__init__(session)
        self._dense = dense
        self._sparse = sparse
        self._config = config or HybridRetrievalConfig()

    def retrieve(self, query: str, *, top_k: int | None = None) -> list[RetrievedChunk]:
        candidate_k = self._config.candidate_k
        dense_results = self._dense.retrieve(query, top_k=candidate_k)
        sparse_results = self._sparse.retrieve(query, top_k=candidate_k)

        dense_map = {chunk.chunk_id: chunk for chunk in dense_results}
        sparse_map = {chunk.chunk_id: chunk for chunk in sparse_results}

        fused = reciprocal_rank_fusion(
            [list(dense_map), list(sparse_map)],
            k=self._config.rrf_k,
            weights=[self._config.dense_weight, self._config.sparse_weight],
        )

        limit = top_k if top_k is not None else candidate_k
        merged: list[RetrievedChunk] = []
        for chunk_id, score in fused:
            chunk = dense_map.get(chunk_id) or sparse_map.get(chunk_id)
            if chunk is None:
                continue
            merged.append(replace(chunk, score=score))
        return merged[:limit]

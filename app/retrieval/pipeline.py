"""Retrieval orchestration pipeline.

Coordinates the dense and sparse search engines, fuses their candidate sets
with Reciprocal Rank Fusion, and applies cross-encoder re-ranking before
surfacing the top results. Each stage is a discrete step so it can be tuned
independently (weights, thresholds) from ``configs/pipelines.yaml``.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import RetrievalConfig, load_runtime_config
from app.retrieval.rerankers import CrossEncoderReRanker
from app.retrieval.retrievers import RetrievedChunk
from app.retrieval.retrievers.dense import DenseRetriever
from app.retrieval.retrievers.hybrid import HybridRetriever
from app.retrieval.retrievers.sparse import SparseRetriever


class RetrievalPipeline:
    """End-to-end hybrid retrieval: fuse candidates, then re-rank.

    Stage 1 gathers ``retrieval.hybrid.candidate_k`` candidates from the dense
    and sparse engines via RRF fusion; stage 2 (optional) re-ranks them with a
    cross-encoder, applying ``rerank.top_k`` and ``rerank.score_threshold``
    before returning.
    """

    def __init__(
        self,
        session: Session,
        *,
        dense: DenseRetriever,
        sparse: SparseRetriever,
        reranker: CrossEncoderReRanker | None = None,
        config: RetrievalConfig | None = None,
    ) -> None:
        self._session = session
        self._dense = dense
        self._sparse = sparse
        self._reranker = reranker
        self._config = config or load_runtime_config().pipelines.retrieval

    def retrieve(self, query: str, *, top_k: int | None = None) -> list[RetrievedChunk]:
        """Return the top-ranked chunks for ``query`` after fusion and re-ranking."""
        hybrid = HybridRetriever(
            self._session,
            dense=self._dense,
            sparse=self._sparse,
            config=self._config.hybrid,
        )
        candidates = hybrid.retrieve(query, top_k=self._config.hybrid.candidate_k)
        if self._reranker is None:
            return candidates[:top_k]
        return self._reranker.rerank(query, candidates, top_k=top_k)

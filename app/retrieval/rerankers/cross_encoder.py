"""Cross-encoder re-ranker integration.

Re-ranks retrieved chunks by scoring each ``(query, chunk.content)`` pair with a
cross-encoder model, overriding the retriever-level dot-product / lexical
scores. The model is injected as a callable so the re-ranker stays
provider-agnostic and unit-testable without loading a model or opening a
network connection.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace

from app.core.config import RerankerConfig
from app.retrieval.retrievers import RetrievedChunk

PairScorer = Callable[[Sequence[tuple[str, str]]], Sequence[float]]


class CrossEncoderReRanker:
    """Re-rank :class:`RetrievedChunk` results with a cross-encoder model.

    When no ``score_pairs`` callable is injected the re-ranker passes results
    through untouched (only applying ``top_k`` trimming), so an orchestrator
    can run against an absent model.
    """

    def __init__(self, config: RerankerConfig, score_pairs: PairScorer | None = None) -> None:
        self._config = config
        self._score_pairs = score_pairs

    def rerank(
        self,
        query: str,
        results: Sequence[RetrievedChunk],
        *,
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievedChunk]:
        """Score each result for ``query`` and return the top-ranked subset.

        Top-``k`` defaults to the configured ``rerank.top_k``; results
        ``score >= threshold`` are kept (threshold defaults to the configured
        ``score_threshold``). When disabled or model-less the input order is
        preserved.
        """
        results = list(results)
        if not self._config.enabled or not results:
            return results[: top_k if top_k is not None else len(results)]

        if self._score_pairs is None:
            return results[: top_k if top_k is not None else len(results)]

        pairs = [(query, chunk.content) for chunk in results]
        scores = self._score_pairs(pairs)
        if len(scores) != len(results):
            msg = f"re-ranker returned {len(scores)} scores for {len(results)} pairs"
            raise ValueError(msg)

        scored = [replace(chunk, score=float(score)) for chunk, score in zip(results, scores, strict=True)]
        threshold = score_threshold if score_threshold is not None else self._config.score_threshold
        if threshold is not None:
            scored = [chunk for chunk in scored if chunk.score >= threshold]
        scored.sort(key=lambda chunk: chunk.score, reverse=True)

        limit = top_k if top_k is not None else self._config.top_k
        return scored[:limit]

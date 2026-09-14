"""Semantic chunker using embedding similarity boundaries."""

from __future__ import annotations

import math
from uuid import UUID

from app.core.config import SemanticChunking
from app.domain.models.chunk import Chunk, ChunkType
from app.ingestion.chunking.base import BaseChunker, Embedder, estimate_tokens, split_sentences


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticChunker(BaseChunker):
    """Splits text into chunks at points where consecutive sentence embeddings diverge.

    With an ``embed_func`` supplied, boundaries are placed where the cosine
    similarity between a sentence and its neighbour falls below
    ``similarity_threshold``. Without an embedder, sentences are packed to a
    fixed ``max_tokens`` budget (fallback to RecursiveChunker-style grouping).
    """

    chunk_type = ChunkType.PARENT

    def __init__(
        self,
        config: SemanticChunking | None = None,
        *,
        embed_func: Embedder | None = None,
        max_tokens: int = 512,
        similarity_threshold: float | None = None,
    ):
        if similarity_threshold is not None and config is not None:
            raise ValueError("Provide either config or similarity_threshold, not both")
        default_threshold = config.similarity_threshold if config else 0.35
        self.threshold = default_threshold if similarity_threshold is None else similarity_threshold
        self.embed_func = embed_func
        self.max_tokens = max_tokens
        self._budget_chars = int(self.max_tokens * 4.0)

    def _chunk(self, text: str, document_id: UUID, document_version_id: UUID) -> list[Chunk]:
        sentences = split_sentences(text)
        if not sentences:
            return []

        # Group sentences into candidate semantic units.
        groups: list[list[str]] = []
        if self.embed_func is not None:
            embeds = self.embed_func(sentences)
            current: list[str] = [sentences[0]]
            for i in range(1, len(sentences)):
                sim = _cosine_similarity(embeds[i - 1], embeds[i])
                if sim < self.threshold or sum(len(s) for s in current) + len(sentences[i]) > self._budget_chars:
                    groups.append(current)
                    current = [sentences[i]]
                else:
                    current.append(sentences[i])
            if current:
                groups.append(current)
        else:
            current = []
            current_len = 0
            for sent in sentences:
                if current and current_len + len(sent) > self._budget_chars:
                    groups.append(current)
                    current = []
                    current_len = 0
                current.append(sent)
                current_len += len(sent)
            if current:
                groups.append(current)

        chunks: list[Chunk] = []
        for i, group in enumerate(groups):
            body = " ".join(group)
            chunks.append(
                Chunk(
                    document_id=document_id,
                    document_version_id=document_version_id,
                    chunk_index=i,
                    chunk_type=self.chunk_type,
                    content=body,
                    token_count=estimate_tokens(body),
                    char_count=len(body),
                )
            )
        return chunks

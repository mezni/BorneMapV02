"""Base embedding contract, token metering, and error types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.config import EmbeddingConfig
from app.domain.models.chunk import Chunk


class EmbeddingError(Exception):
    """Base error for embedding generation failures."""


class EmbeddingCallError(EmbeddingError):
    """Raised when a provider call fails despite retries or returns malformed data."""


class EmbeddingResult(BaseModel):
    """Outcome of an embedding run over one or more texts."""

    model_config = ConfigDict(extra="forbid")

    embeddings: list[list[float]]
    model: str
    dimensions: int
    input_tokens: int
    batch_count: int


class TokenMeter:
    """Tracks embedding token usage and estimated cost for FinOps accounting."""

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        dimensions: int,
        cost_per_1m_tokens: float = 0.0,
    ) -> None:
        self.provider = provider
        self.model = model
        self.dimensions = dimensions
        self.cost_per_1m_tokens = cost_per_1m_tokens
        self.reset()

    @property
    def total_input_tokens(self) -> int:
        return self._input_tokens

    @property
    def batch_count(self) -> int:
        return self._batch_count

    @property
    def estimated_cost_usd(self) -> float:
        return self._input_tokens * (self.cost_per_1m_tokens / 1_000_000)

    def record(self, input_tokens: int) -> None:
        """Record the input tokens consumed by one provider call."""
        if input_tokens < 0:
            msg = f"input_tokens must be non-negative, got {input_tokens}"
            raise ValueError(msg)
        self._input_tokens += input_tokens
        self._batch_count += 1

    def reset(self) -> None:
        """Zero all counters for a fresh ingestion run."""
        self._input_tokens = 0
        self._batch_count = 0

    def snapshot(self) -> dict[str, Any]:
        """Return a plain mapping suitable for PipelineRun metadata."""
        return {
            "provider": self.provider,
            "model": self.model,
            "dimensions": self.dimensions,
            "total_input_tokens": self._input_tokens,
            "batch_count": self._batch_count,
            "estimated_cost_usd": self.estimated_cost_usd,
        }


class BaseEmbeddingGenerator(ABC):
    """Contract for all embedding backends.

    Concrete implementations define ``_embed_batch``; ``embed_texts`` handles
    input validation, batching, dimension checks, and token metering.
    """

    def __init__(self, config: EmbeddingConfig, *, meter: TokenMeter | None = None) -> None:
        self.config = config
        self._meter = meter or TokenMeter(
            provider=config.provider,
            model=config.model,
            dimensions=config.dimensions,
        )

    @property
    def model(self) -> str:
        return self.config.model

    @property
    def dimensions(self) -> int:
        return self.config.dimensions

    @property
    def batch_size(self) -> int:
        return self.config.batch_size

    @property
    def meter(self) -> TokenMeter:
        return self._meter

    def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        """Embed a list of texts in config-sized batches."""
        if not texts:
            msg = "Cannot embed an empty list of texts"
            raise EmbeddingError(msg)
        if any(not text.strip() for text in texts):
            msg = "Cannot embed empty strings"
            raise EmbeddingError(msg)

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            batch_vectors, batch_tokens = self._embed_batch(batch)
            if any(len(vector) != self.dimensions for vector in batch_vectors):
                msg = f"Embedding dimensionality mismatch: expected {self.dimensions}, got a different size"
                raise EmbeddingError(msg)
            vectors.extend(batch_vectors)
            self.meter.record(batch_tokens)

        return EmbeddingResult(
            embeddings=vectors,
            model=self.model,
            dimensions=self.dimensions,
            input_tokens=self.meter.total_input_tokens,
            batch_count=self.meter.batch_count,
        )

    def embed_chunks(self, chunks: list[Chunk]) -> EmbeddingResult:
        """Embed chunk contents and attach the vectors back onto each Chunk."""
        result = self.embed_texts([chunk.content for chunk in chunks])
        for chunk, vector in zip(chunks, result.embeddings, strict=True):
            chunk.embedding = vector
        return result

    def reset(self) -> None:
        """Reset the token meter for a new run."""
        self.meter.reset()

    @abstractmethod
    def _embed_batch(self, batch: list[str]) -> tuple[list[list[float]], int]:
        """Embed one batch of texts; return (vectors, input_tokens)."""
        raise NotImplementedError

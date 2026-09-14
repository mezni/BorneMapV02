"""Embedding generation for the ingestion pipeline (LiteLLM-backed)."""

from __future__ import annotations

from app.core.config import EmbeddingConfig, PricingConfig, TimeoutConfig
from app.ingestion.embeddings.base import (
    BaseEmbeddingGenerator,
    EmbeddingCallError,
    EmbeddingError,
    EmbeddingResult,
    TokenMeter,
)
from app.ingestion.embeddings.litellm_generator import LiteLLMEmbeddingGenerator


def get_embedding_generator(
    config: EmbeddingConfig,
    *,
    timeouts: TimeoutConfig | None = None,
    pricing: PricingConfig | None = None,
) -> BaseEmbeddingGenerator:
    """Instantiate the configured embedding generator (LiteLLM-backed)."""
    return LiteLLMEmbeddingGenerator(config, timeouts=timeouts, pricing=pricing)


__all__ = [
    "BaseEmbeddingGenerator",
    "EmbeddingCallError",
    "EmbeddingError",
    "EmbeddingResult",
    "LiteLLMEmbeddingGenerator",
    "TokenMeter",
    "get_embedding_generator",
]

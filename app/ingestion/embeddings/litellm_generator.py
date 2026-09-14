"""LiteLLM-backed embedding generator with retries and token metering."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from app.core.config import EmbeddingConfig, PricingConfig, TimeoutConfig
from app.ingestion.chunking.base import estimate_tokens
from app.ingestion.embeddings.base import (
    BaseEmbeddingGenerator,
    EmbeddingCallError,
    EmbeddingError,
    TokenMeter,
)


def _load_litellm() -> Any:
    """Import the optional litellm backend, raising a clear install hint if absent."""
    try:
        import litellm  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        msg = "litellm is not installed; install it with: uv add litellm"
        raise EmbeddingError(msg) from exc
    return litellm


class LiteLLMEmbeddingGenerator(BaseEmbeddingGenerator):
    """Embedding generator backed by LiteLLM's unified provider API.

    Lazily imports ``litellm`` so the module remains importable without the
    optional dependency; using it without litellm raises an install-hint
    ``EmbeddingError``. Provider calls are retried with exponential backoff
    using the configured timeout/retry settings.
    """

    def __init__(
        self,
        config: EmbeddingConfig,
        *,
        meter: TokenMeter | None = None,
        timeouts: TimeoutConfig | None = None,
        pricing: PricingConfig | None = None,
        retries: int | None = None,
        backoff_factor: float | None = None,
        request_timeout_seconds: float | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(config, meter=meter)
        if pricing is not None:
            self.meter.cost_per_1m_tokens = pricing.embedding_usd_per_1m_tokens
        timeout_config = timeouts or TimeoutConfig()
        self.retries = timeout_config.retries if retries is None else retries
        self.backoff_factor = timeout_config.backoff_factor if backoff_factor is None else backoff_factor
        self.request_timeout_seconds = (
            timeout_config.request_timeout_seconds if request_timeout_seconds is None else request_timeout_seconds
        )
        self._sleep = sleep
        self._litellm: Any | None = None

    def _backend(self) -> Any:
        """Return the lazily imported litellm module."""
        if self._litellm is None:
            self._litellm = _load_litellm()
        return self._litellm

    def _embed_batch(self, batch: list[str]) -> tuple[list[list[float]], int]:
        backend = self._backend()
        last_error: Exception | None = None
        max_attempts = self.retries + 1
        for attempt in range(max_attempts):
            try:
                return self._call_provider(backend, batch)
            except EmbeddingCallError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt + 1 < max_attempts:
                    self._sleep(self.backoff_factor * (2**attempt))
        assert last_error is not None
        msg = f"Embedding call failed after {max_attempts} attempts: {last_error}"
        raise EmbeddingCallError(msg) from last_error

    def _call_provider(self, backend: Any, batch: list[str]) -> tuple[list[list[float]], int]:
        response = backend.embedding(
            model=self.model,
            input=batch,
            timeout=self.request_timeout_seconds,
        )
        data = getattr(response, "data", None)
        if not isinstance(data, list):
            msg = "Embedding provider returned no data payload"
            raise EmbeddingCallError(msg)
        vectors = [list(item["embedding"]) for item in data]
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0) if usage is not None else 0
        tokens = prompt_tokens or sum(estimate_tokens(text) for text in batch)
        return vectors, tokens

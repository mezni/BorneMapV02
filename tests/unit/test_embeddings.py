"""Unit tests for the embedding generators and token metering."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from app.core.config import EmbeddingConfig, PricingConfig, TimeoutConfig
from app.domain.models.chunk import Chunk
from app.ingestion.embeddings import (
    BaseEmbeddingGenerator,
    EmbeddingCallError,
    EmbeddingError,
    EmbeddingResult,
    LiteLLMEmbeddingGenerator,
    TokenMeter,
    get_embedding_generator,
)

CONFIG = EmbeddingConfig(provider="openai", model="text-embedding-3-small", dimensions=3, batch_size=2)
PRICING = PricingConfig(
    currency="USD",
    chat_input_usd_per_1k_tokens=0.150,
    chat_output_usd_per_1k_tokens=0.600,
    embedding_usd_per_1m_tokens=1.0,
)


class _StubGenerator(BaseEmbeddingGenerator):
    def __init__(
        self,
        *,
        batch_vectors: list[list[float]] | None = None,
        batch_tokens: int = 9,
        raise_on: list[str] | None = None,
    ) -> None:
        super().__init__(CONFIG, meter=TokenMeter(provider=CONFIG.provider, model=CONFIG.model, dimensions=3))
        self.batch_vectors = batch_vectors or [[0.1, 0.2, 0.3]]
        self.batch_tokens = batch_tokens
        self.raise_on = raise_on or []
        self.calls: list[list[str]] = []

    def _embed_batch(self, batch: list[str]) -> tuple[list[list[float]], int]:
        self.calls.append(batch)
        if self.raise_on and batch[0] in self.raise_on:
            raise EmbeddingError(f"boom: {batch[0]}")
        return [list(self.batch_vectors[i % len(self.batch_vectors)]) for i in range(len(batch))], self.batch_tokens


class _FakeLitellm:
    def __init__(
        self,
        *,
        vectors: list[list[float]] | None = None,
        prompt_tokens: int = 0,
        fails: int = 0,
        no_data: bool = False,
    ) -> None:
        self.vectors = vectors or [[0.5, 0.5, 0.5], [0.6, 0.6, 0.6]]
        self.prompt_tokens = prompt_tokens
        self.fails = fails
        self.no_data = no_data
        self.calls = 0

    def embedding(self, **kwargs: Any) -> Any:
        self.calls += 1
        if self.fails > 0:
            self.fails -= 1
            raise ConnectionError("transient failure")
        if self.no_data:
            return _Resp(data=None)
        return _Resp(
            data=[{"embedding": self.vectors[i % len(self.vectors)]} for i in range(len(kwargs["input"]))],
            prompt_tokens=self.prompt_tokens,
        )


class _Resp:
    def __init__(self, *, data: Any, prompt_tokens: int = 0) -> None:
        self.data = data
        self.usage = _Usage(prompt_tokens)


class _Usage:
    def __init__(self, prompt_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens


# ---------------------------------------------------------------------------
# TokenMeter
# ---------------------------------------------------------------------------


class TestTokenMeter:
    def test_records_tokens_and_batch_count(self) -> None:
        meter = TokenMeter(provider="openai", model="m", dimensions=3)
        meter.record(10)
        meter.record(5)
        assert meter.total_input_tokens == 15
        assert meter.batch_count == 2

    def test_cost_estimation_uses_per_million_rate(self) -> None:
        meter = TokenMeter(provider="openai", model="m", dimensions=3, cost_per_1m_tokens=1.0)
        meter.record(1_000_000)
        assert meter.estimated_cost_usd == 1.0

    def test_reset_clears_counters(self) -> None:
        meter = TokenMeter(provider="openai", model="m", dimensions=3)
        meter.record(42)
        meter.reset()
        assert meter.total_input_tokens == 0
        assert meter.batch_count == 0

    def test_negative_tokens_rejected(self) -> None:
        meter = TokenMeter(provider="openai", model="m", dimensions=3)
        with pytest.raises(ValueError, match="non-negative"):
            meter.record(-1)

    def test_snapshot_shape(self) -> None:
        meter = TokenMeter(provider="openai", model="m", dimensions=3)
        meter.record(7)
        data = meter.snapshot()
        assert data["model"] == "m"
        assert data["total_input_tokens"] == 7
        assert data["batch_count"] == 1


# ---------------------------------------------------------------------------
# BaseEmbeddingGenerator
# ---------------------------------------------------------------------------


class TestBaseEmbeddingGenerator:
    def test_embeds_and_meters_multi_batch(self) -> None:
        gen = _StubGenerator(batch_tokens=9)
        result = gen.embed_texts(["one", "two", "three", "four", "five"])
        assert len(result.embeddings) == 5
        assert result.batch_count == 3
        assert result.input_tokens == 27
        assert gen.meter.total_input_tokens == 27

    def test_empty_list_rejected(self) -> None:
        with pytest.raises(EmbeddingError, match="empty list"):
            _StubGenerator().embed_texts([])

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(EmbeddingError, match="empty strings"):
            _StubGenerator().embed_texts(["   "])

    def test_dimension_mismatch_raises(self) -> None:
        gen = _StubGenerator(batch_vectors=[[0.1, 0.2]])
        with pytest.raises(EmbeddingError, match="dimensionality"):
            gen.embed_texts(["one"])

    def test_embed_chunks_attaches_vectors(self) -> None:
        gen = _StubGenerator(batch_vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        chunks = [
            Chunk(document_id=uuid4(), document_version_id=uuid4(), content="alpha"),
            Chunk(document_id=uuid4(), document_version_id=uuid4(), content="beta"),
        ]
        result = gen.embed_chunks(chunks)
        assert result.embeddings[0] == [0.1, 0.2, 0.3]
        assert chunks[0].embedding == [0.1, 0.2, 0.3]
        assert chunks[1].embedding == [0.4, 0.5, 0.6]

    def test_reset_clears_meter(self) -> None:
        gen = _StubGenerator(batch_tokens=9)
        gen.embed_texts(["a", "b", "c", "d"])
        assert gen.meter.total_input_tokens > 0
        gen.reset()
        assert gen.meter.total_input_tokens == 0

    def test_result_model_rejects_extra_fields(self) -> None:
        with pytest.raises(ValueError):
            EmbeddingResult.model_validate({"embeddings": [], "model": "m", "dimensions": 3, "extra": 1})


# ---------------------------------------------------------------------------
# LiteLLMEmbeddingGenerator
# ---------------------------------------------------------------------------


class _TestLiteLLMGenerator(LiteLLMEmbeddingGenerator):
    def __init__(self, backend: Any, *, sleep_impl: Any = lambda _: None, **kwargs: Any) -> None:
        super().__init__(CONFIG, sleep=sleep_impl, **kwargs)
        self._litellm = backend


class TestLiteLLMEmbeddingGenerator:
    def test_install_hint_when_litellm_missing(self) -> None:
        with pytest.raises(EmbeddingError, match="uv add litellm"):
            LiteLLMEmbeddingGenerator(CONFIG)._backend()

    def test_embeds_using_provider_response(self) -> None:
        backend = _FakeLitellm(prompt_tokens=7)
        gen = _TestLiteLLMGenerator(backend)
        result = gen.embed_texts(["a", "b"])
        assert len(result.embeddings) == 2
        assert result.input_tokens == 7
        assert backend.calls == 1

    def test_token_fallback_to_estimate_when_usage_missing(self) -> None:
        backend = _FakeLitellm(prompt_tokens=0)
        gen = _TestLiteLLMGenerator(backend)
        result = gen.embed_texts(["abcdefgh", "abcd"])
        assert result.input_tokens == 3  # 2 tokens + 1 token

    def test_retries_then_succeeds(self) -> None:
        sleeps: list[float] = []
        backend = _FakeLitellm(prompt_tokens=5, fails=2)
        gen = _TestLiteLLMGenerator(backend, retries=3, backoff_factor=2.0, sleep_impl=sleeps.append)
        result = gen.embed_texts(["a"])
        assert result.input_tokens == 5
        assert backend.calls == 3  # 2 failures + 1 success
        assert sleeps == [2.0, 4.0]

    def test_retries_exhausted_raises_call_error(self) -> None:
        backend = _FakeLitellm(fails=99)
        gen = _TestLiteLLMGenerator(backend, retries=1, backoff_factor=1.0)
        with pytest.raises(EmbeddingCallError, match="2 attempts"):
            gen.embed_texts(["a"])
        assert backend.calls == 2

    def test_malformed_response_is_not_retried(self) -> None:
        backend = _FakeLitellm(no_data=True)
        gen = _TestLiteLLMGenerator(backend, retries=3)
        with pytest.raises(EmbeddingCallError, match="no data"):
            gen.embed_texts(["a"])
        assert backend.calls == 1


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestGetEmbeddingGenerator:
    def test_factory_returns_litellm_generator(self) -> None:
        gen = get_embedding_generator(CONFIG)
        assert isinstance(gen, LiteLLMEmbeddingGenerator)
        assert gen.model == "text-embedding-3-small"
        assert gen.dimensions == 3
        assert gen.batch_size == 2

    def test_factory_wires_pricing_and_timeouts(self) -> None:
        gen = get_embedding_generator(
            CONFIG,
            pricing=PRICING,
            timeouts=TimeoutConfig(retries=5, backoff_factor=3.0),
        )
        assert isinstance(gen, LiteLLMEmbeddingGenerator)
        assert gen.meter.cost_per_1m_tokens == 1.0
        assert gen.retries == 5
        assert gen.backoff_factor == 3.0

    def test_default_timeout_config(self) -> None:
        gen = get_embedding_generator(CONFIG)
        assert isinstance(gen, LiteLLMEmbeddingGenerator)
        assert gen.retries == 3
        assert gen.backoff_factor == 2.0
        assert gen.request_timeout_seconds == 30.0

"""Unit tests for the YAML config parser and Pydantic validation engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from app.core.config import (
    ConfigLoadError,
    ConfigValidationError,
    DatabaseConfig,
    LLMConfig,
    PipelinesConfig,
    PromptsConfig,
    RuntimeConfig,
    Settings,
    _read_yaml,
    get_settings,
    load_runtime_config,
)
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Fixture data builders
# ---------------------------------------------------------------------------


def _llm_data(dimensions: int = 1536) -> dict[str, Any]:
    return {
        "chat": {
            "primary": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.0},
            "fallback": {"provider": "anthropic", "model": "claude-3-5-sonnet-latest", "temperature": 0.0},
            "max_tokens": 2048,
        },
        "embeddings": {
            "provider": "openai",
            "model": "text-embedding-3-small",
            "dimensions": dimensions,
            "batch_size": 64,
        },
        "timeouts": {
            "request_timeout_seconds": 30.0,
            "connect_timeout_seconds": 5.0,
            "retries": 3,
            "backoff_factor": 2.0,
        },
        "pricing": {
            "currency": "USD",
            "chat_input_usd_per_1k_tokens": 0.15,
            "chat_output_usd_per_1k_tokens": 0.60,
            "embedding_usd_per_1m_tokens": 0.02,
        },
    }


def _prompts_data() -> dict[str, Any]:
    return {
        "default_prompt_id": "grounded_answer",
        "prompts": [
            {
                "id": "grounded_answer",
                "version": "1.0",
                "system_prompt": "Answer using ONLY the provided context.",
                "citation_instructions": "Cite as [source:N].",
                "variables": {
                    "context": {"required": True, "description": "retrieved context"},
                    "question": {"required": True, "description": "user question"},
                },
            }
        ],
    }


def _pipelines_data(rrf_k: int = 60, strategy: str = "parent_child") -> dict[str, Any]:
    return {
        "ingestion": {
            "max_file_size_mb": 25,
            "allowed_extensions": ["pdf", "md"],
            "storage_driver": "local",
            "batch_size": 10,
        },
        "chunking": {"strategy": strategy},
        "retrieval": {
            "dense": {"top_k": 20, "ef_search": 40},
            "sparse": {"top_k": 20},
            "hybrid": {"rrf_k": rrf_k, "dense_weight": 1.0, "sparse_weight": 1.0, "candidate_k": 100},
            "rerank": {"enabled": True, "model": "cross_encoder/ms-marco", "top_k": 5, "score_threshold": 0.5},
        },
    }


def _database_data(m: int = 16, ef_construction: int = 64, dims: int = 1536) -> dict[str, Any]:
    return {
        "connection": {
            "url": "postgresql+asyncpg://aether:aether@localhost:5432/aether_rag",
            "pool_size": 10,
            "max_overflow": 5,
            "pool_timeout_seconds": 30.0,
            "echo": False,
        },
        "vector_index": {"dims": dims, "m": m, "ef_construction": ef_construction, "distance": "cosine"},
        "fulltext": {"language": "english", "tsvector_config": "english"},
    }


def _runtime_data(dims: int = 1536) -> dict[str, Any]:
    return {
        "llm": _llm_data(dimensions=dims),
        "prompts": _prompts_data(),
        "pipelines": _pipelines_data(),
        "database": _database_data(dims=dims),
    }


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class TestSettings:
    def test_defaults(self) -> None:
        settings = Settings()
        assert settings.environment == "dev"
        assert settings.configs_dir.name == "configs"

    def test_default_configs_dir_contains_yaml_files(self) -> None:
        settings = Settings()
        assert (settings.configs_dir / "llm.yaml").is_file()
        assert (settings.configs_dir / "prompts.yaml").is_file()

    def test_environment_variable_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AETHER_ENVIRONMENT", "prod")
        monkeypatch.setenv("AETHER_CONFIGS_DIR", "/tmp/aether-override")
        settings = Settings()
        assert settings.environment == "prod"
        assert settings.configs_dir == Path("/tmp/aether-override")

    def test_config_path_missing_raises(self, tmp_path: Path) -> None:
        settings = Settings(configs_dir=tmp_path)
        with pytest.raises(ConfigLoadError, match="not found"):
            settings.config_path("llm.yaml")

    def test_get_settings_is_cached_singleton(self) -> None:
        assert get_settings() is get_settings()


# ---------------------------------------------------------------------------
# Low-level YAML reader
# ---------------------------------------------------------------------------


class TestReadYaml:
    def test_reads_valid_mapping(self, tmp_path: Path) -> None:
        path = tmp_path / "values.yaml"
        path.write_text("a: 1\nb:\n  - x\n  - y\n", encoding="utf-8")
        assert _read_yaml(path) == {"a": 1, "b": ["x", "y"]}

    def test_missing_file_raises_load_error(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigLoadError):
            _read_yaml(tmp_path / "missing.yaml")

    def test_invalid_yaml_raises_load_error(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text("a: [unterminated\n", encoding="utf-8")
        with pytest.raises(ConfigLoadError, match="Invalid YAML"):
            _read_yaml(path)

    def test_non_mapping_top_level_raises_load_error(self, tmp_path: Path) -> None:
        path = tmp_path / "list.yaml"
        path.write_text("- 1\n- 2\n", encoding="utf-8")
        with pytest.raises(ConfigLoadError, match="mapping"):
            _read_yaml(path)


# ---------------------------------------------------------------------------
# llm.yaml
# ---------------------------------------------------------------------------


class TestLLMConfig:
    def test_accepts_valid_payload(self) -> None:
        config = LLMConfig.model_validate(_llm_data())
        assert config.chat.primary.provider == "openai"
        assert config.chat.fallback is not None
        assert config.embeddings.dimensions == 1536

    def test_temperature_out_of_range_rejected(self) -> None:
        data = _llm_data()
        data["chat"]["primary"]["temperature"] = 3.0
        with pytest.raises(ValidationError):
            LLMConfig.model_validate(data)

    def test_pricing_must_be_positive(self) -> None:
        data = _llm_data()
        data["pricing"]["embedding_usd_per_1m_tokens"] = -0.01
        with pytest.raises(ValidationError):
            LLMConfig.model_validate(data)

    def test_extra_keys_rejected(self) -> None:
        data = _llm_data()
        data["surprise"] = True
        with pytest.raises(ValidationError):
            LLMConfig.model_validate(data)


# ---------------------------------------------------------------------------
# prompts.yaml
# ---------------------------------------------------------------------------


class TestPromptsConfig:
    def test_parses_prompt_variables(self) -> None:
        config = PromptsConfig.model_validate(_prompts_data())
        prompt = config.prompts[0]
        assert config.default_prompt_id == "grounded_answer"
        assert prompt.version == "1.0"
        assert prompt.variables["context"].required is True
        assert prompt.variables["question"].description == "user question"

    def test_missing_default_prompt_id_rejected(self) -> None:
        data = _prompts_data()
        del data["default_prompt_id"]
        with pytest.raises(ValidationError):
            PromptsConfig.model_validate(data)


# ---------------------------------------------------------------------------
# pipelines.yaml
# ---------------------------------------------------------------------------


class TestPipelinesConfig:
    def test_accepts_valid_payload(self) -> None:
        config = PipelinesConfig.model_validate(_pipelines_data())
        assert config.retrieval.hybrid.rrf_k == 60
        assert config.chunking.strategy == "parent_child"

    def test_non_positive_rrf_k_rejected(self) -> None:
        with pytest.raises(ValidationError, match="rrf_k"):
            PipelinesConfig.model_validate(_pipelines_data(rrf_k=0))

    def test_invalid_chunking_strategy_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PipelinesConfig.model_validate(_pipelines_data(strategy="blocky"))


# ---------------------------------------------------------------------------
# database.yaml
# ---------------------------------------------------------------------------


class TestDatabaseConfig:
    def test_accepts_valid_payload(self) -> None:
        config = DatabaseConfig.model_validate(_database_data())
        assert config.vector_index.m == 16
        assert config.vector_index.ef_construction == 64

    def test_hnsw_ef_construction_too_small_rejected(self) -> None:
        with pytest.raises(ValidationError, match="ef_construction"):
            DatabaseConfig.model_validate(_database_data(m=50, ef_construction=64))

    def test_invalid_distance_metric_rejected(self) -> None:
        data = _database_data()
        data["vector_index"]["distance"] = "hamming"
        with pytest.raises(ValidationError):
            DatabaseConfig.model_validate(data)

    def test_extra_keys_rejected(self) -> None:
        data = _database_data()
        data["extra"] = "nope"
        with pytest.raises(ValidationError):
            DatabaseConfig.model_validate(data)


# ---------------------------------------------------------------------------
# Aggregated RuntimeConfig
# ---------------------------------------------------------------------------


class TestRuntimeConfig:
    def test_accepts_cross_valid_payload(self) -> None:
        config = RuntimeConfig.model_validate(_runtime_data())
        assert config.llm.embeddings.dimensions == config.database.vector_index.dims

    def test_embedding_and_vector_dim_mismatch_rejected(self) -> None:
        data = _runtime_data()
        data["llm"]["embeddings"]["dimensions"] = 3072
        with pytest.raises(ValidationError, match="dimensions"):
            RuntimeConfig.model_validate(data)


# ---------------------------------------------------------------------------
# load_runtime_config
# ---------------------------------------------------------------------------


class TestLoadRuntimeConfig:
    def test_loads_repo_configs(self) -> None:
        config = load_runtime_config()
        assert config.llm.chat.primary.model
        assert config.prompts.default_prompt_id
        assert config.pipelines.retrieval.rerank.model
        assert config.database.connection.url

    def test_missing_config_directory_raises_load_error(self, tmp_path: Path) -> None:
        settings = Settings(configs_dir=tmp_path / "does-not-exist")
        with pytest.raises(ConfigLoadError):
            load_runtime_config(settings)

    def test_invalid_prompts_yaml_raises_validation_error(self, settings: Settings) -> None:
        (settings.configs_dir / "prompts.yaml").write_text("default_prompt_id: 42\n", encoding="utf-8")
        with pytest.raises(ConfigValidationError) as exc_info:
            load_runtime_config(settings)
        assert exc_info.value.file_name == "prompts.yaml"

    def test_cross_file_dimension_mismatch_raises_validation_error(self, settings: Settings) -> None:
        llm_path = settings.configs_dir / "llm.yaml"
        llm_path.write_text(
            llm_path.read_text(encoding="utf-8").replace("dimensions: 1536", "dimensions: 2048"),
            encoding="utf-8",
        )
        with pytest.raises(ConfigValidationError) as exc_info:
            load_runtime_config(settings)
        assert exc_info.value.file_name == "runtime-config"

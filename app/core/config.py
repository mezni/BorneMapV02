"""
YAML configuration parser and Pydantic validation engine.

Loads operational configs from configs/*.yaml at startup and validates them
through strict Pydantic models. Environment overrides are handled by the
Settings class (pydantic-settings); YAML files remain the single source of
truth for all operational parameters.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ConfigError(Exception):
    """Base error for configuration loading failures."""


class ConfigLoadError(ConfigError):
    """Raised when a YAML file cannot be read or contains invalid YAML."""


class ConfigValidationError(ConfigError):
    """Raised when YAML content fails Pydantic schema validation."""

    def __init__(self, file_name: str, errors: Any) -> None:
        self.file_name = file_name
        self.raw_errors = errors
        super().__init__(f"Validation failed for {file_name}")


# ---------------------------------------------------------------------------
# Runtime environment settings (env vars / .env file)
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """Environment-driven runtime settings. Prefix: AETHER_."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AETHER_",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    environment: Literal["dev", "staging", "prod"] = "dev"
    configs_dir: Path = Path(__file__).resolve().parents[2] / "configs"

    def config_path(self, filename: str) -> Path:
        """Return the resolved config path, raising if it does not exist."""
        path = self.configs_dir / filename
        if not path.is_file():
            msg = f"Config file not found: {path}"
            raise ConfigLoadError(msg)
        return path


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached, frozen Settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------


def _read_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML file and return a Python mapping."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"Cannot read file {path}: {exc}"
        raise ConfigLoadError(msg) from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        msg = f"Invalid YAML in {path}: {exc}"
        raise ConfigLoadError(msg) from exc
    if not isinstance(data, dict):
        msg = f"Top-level value in {path} must be a mapping, got {type(data).__name__}"
        raise ConfigLoadError(msg)
    return data


# ---------------------------------------------------------------------------
# llm.yaml models
# ---------------------------------------------------------------------------


class ChatModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)


class ChatConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: ChatModelConfig
    fallback: ChatModelConfig | None = None
    max_tokens: int = Field(default=2048, gt=0)


class EmbeddingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    dimensions: int = Field(gt=0)
    batch_size: int = Field(default=64, gt=0)


class TimeoutConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_timeout_seconds: float = Field(default=30.0, gt=0)
    connect_timeout_seconds: float = Field(default=5.0, gt=0)
    retries: int = Field(default=3, ge=0)
    backoff_factor: float = Field(default=2.0, ge=0)


class PricingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str = "USD"
    chat_input_usd_per_1k_tokens: float = Field(gt=0)
    chat_output_usd_per_1k_tokens: float = Field(gt=0)
    embedding_usd_per_1m_tokens: float = Field(gt=0)


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chat: ChatConfig
    embeddings: EmbeddingConfig
    timeouts: TimeoutConfig
    pricing: PricingConfig


# ---------------------------------------------------------------------------
# prompts.yaml models
# ---------------------------------------------------------------------------


class PromptVariable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: bool = True
    description: str | None = None


class PromptDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    version: str
    description: str | None = None
    system_prompt: str
    citation_instructions: str | None = None
    variables: dict[str, PromptVariable] = {}


class PromptsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_prompt_id: str
    prompts: list[PromptDefinition]


# ---------------------------------------------------------------------------
# pipelines.yaml models
# ---------------------------------------------------------------------------


class IngestionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_file_size_mb: int = Field(default=25, gt=0)
    allowed_extensions: list[str] = Field(default_factory=list)
    storage_driver: str = "local"
    batch_size: int = Field(default=10, gt=0)


class RecursiveChunking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_size: int = Field(default=512, gt=0)
    chunk_overlap: int = Field(default=64, ge=0)


class ParentChildChunking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_chunk_size: int = Field(default=1536, gt=0)
    child_chunk_size: int = Field(default=512, gt=0)
    child_chunk_overlap: int = Field(default=64, ge=0)


class SemanticChunking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    similarity_threshold: float = Field(default=0.35, gt=0.0, lt=1.0)


class ChunkingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: Literal["recursive", "semantic", "parent_child"] = "parent_child"
    recursive: RecursiveChunking = RecursiveChunking()
    parent_child: ParentChildChunking = ParentChildChunking()
    semantic: SemanticChunking = SemanticChunking()


class DenseRetrievalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_k: int = Field(default=20, gt=0)
    ef_search: int = Field(default=40, gt=0)


class SparseRetrievalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_k: int = Field(default=20, gt=0)


class HybridRetrievalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rrf_k: int = Field(default=60, gt=0)
    dense_weight: float = Field(default=1.0, gt=0)
    sparse_weight: float = Field(default=1.0, gt=0)
    candidate_k: int = Field(default=100, gt=0)


class RerankerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    model: str
    top_k: int = Field(default=5, gt=0)
    score_threshold: float = Field(default=0.50, ge=0.0, le=1.0)


class RetrievalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dense: DenseRetrievalConfig = DenseRetrievalConfig()
    sparse: SparseRetrievalConfig = SparseRetrievalConfig()
    hybrid: HybridRetrievalConfig = HybridRetrievalConfig()
    rerank: RerankerConfig

    @model_validator(mode="after")
    def _validate_rrf_k(self) -> RetrievalConfig:
        if self.hybrid.rrf_k <= 0:
            msg = "retrieval.hybrid.rrf_k must be positive"
            raise ValueError(msg)
        return self


class PipelinesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingestion: IngestionConfig = IngestionConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    retrieval: RetrievalConfig


# ---------------------------------------------------------------------------
# database.yaml models
# ---------------------------------------------------------------------------


class DatabaseConnectionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    pool_size: int = Field(default=10, gt=0)
    max_overflow: int = Field(default=5, ge=0)
    pool_timeout_seconds: float = Field(default=30.0, gt=0)
    echo: bool = False


class VectorIndexConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dims: int = Field(gt=0)
    m: int = Field(default=16, gt=0)
    ef_construction: int = Field(default=64, gt=0)
    distance: Literal["cosine", "l2", "inner_product"] = "cosine"


class FulltextConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str = "english"
    tsvector_config: str = "english"


class DatabaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection: DatabaseConnectionConfig
    vector_index: VectorIndexConfig
    fulltext: FulltextConfig = FulltextConfig()

    @model_validator(mode="after")
    def _validate_hnsw_index(self) -> DatabaseConfig:
        vi = self.vector_index
        if vi.m * 2 > vi.ef_construction:
            msg = f"vector_index.m ({vi.m}) * 2 must be <= vector_index.ef_construction ({vi.ef_construction})"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# Aggregated runtime config
# ---------------------------------------------------------------------------


class RuntimeConfig(BaseModel):
    """Fully validated, aggregated view of every operational YAML config."""

    model_config = ConfigDict(extra="forbid")

    llm: LLMConfig
    prompts: PromptsConfig
    pipelines: PipelinesConfig
    database: DatabaseConfig

    @model_validator(mode="after")
    def _validate_embedding_dims(self) -> RuntimeConfig:
        llm_emb = self.llm.embeddings.dimensions
        db_vec = self.database.vector_index.dims
        if llm_emb != db_vec:
            msg = f"llm.embeddings.dimensions ({llm_emb}) does not match database.vector_index.dims ({db_vec})"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _load_file[T: BaseModel](model: type[T], path: Path) -> T:
    """Read a YAML file, validate against a Pydantic model, return the instance."""
    data = _read_yaml(path)
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise ConfigValidationError(path.name, exc) from exc


def load_runtime_config(settings: Settings | None = None) -> RuntimeConfig:
    """
    Load and cross-validate every YAML config file.

    Raises ConfigLoadError for file-system or YAML syntax issues,
    or ConfigValidationError when content fails schema validation.
    """
    settings = settings or get_settings()
    llm = _load_file(LLMConfig, settings.config_path("llm.yaml"))
    prompts = _load_file(PromptsConfig, settings.config_path("prompts.yaml"))
    pipelines = _load_file(PipelinesConfig, settings.config_path("pipelines.yaml"))
    database = _load_file(DatabaseConfig, settings.config_path("database.yaml"))
    try:
        return RuntimeConfig(llm=llm, prompts=prompts, pipelines=pipelines, database=database)
    except ValidationError as exc:
        raise ConfigValidationError("runtime-config", exc) from exc

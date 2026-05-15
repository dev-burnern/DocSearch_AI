from functools import lru_cache
import os
from typing import Literal

from pydantic import BaseModel, Field


DEFAULT_API_KEY = "local-dev-key"
DEFAULT_API_KEYS = f"{DEFAULT_API_KEY}|local-workspace|Local Workspace"


def _bool_env(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() == "true"


def _is_production_env() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() == "production"


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return None
    return value


class Settings(BaseModel):
    app_name: str = Field(
        default_factory=lambda: os.getenv("APP_NAME", "DocSearch AI"),
    )
    app_env: str = Field(
        default_factory=lambda: os.getenv("APP_ENV", "development"),
    )
    debug: bool = Field(
        default_factory=lambda: _bool_env("DEBUG", False),
    )
    api_keys: str = Field(
        default_factory=lambda: os.getenv(
            "DOCSEARCH_API_KEYS",
            DEFAULT_API_KEYS,
        ),
    )
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql://docsearch:docsearch@postgres:5432/docsearch",
        ),
    )
    minio_endpoint: str = Field(
        default_factory=lambda: os.getenv("MINIO_ENDPOINT", "minio:9000"),
    )
    minio_access_key: str = Field(
        default_factory=lambda: os.getenv("MINIO_ACCESS_KEY", "minio"),
    )
    minio_secret_key: str = Field(
        default_factory=lambda: os.getenv("MINIO_SECRET_KEY", "minio123"),
    )
    minio_bucket: str = Field(
        default_factory=lambda: os.getenv("MINIO_BUCKET", "documents"),
    )
    minio_secure: bool = Field(
        default_factory=lambda: _bool_env("MINIO_SECURE", False),
    )
    redis_url: str = Field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://redis:6379/0"),
    )
    indexing_queue_backend: str = Field(
        default_factory=lambda: os.getenv("INDEXING_QUEUE_BACKEND", "inprocess"),
    )
    chunk_max_characters: int = Field(
        default_factory=lambda: int(os.getenv("CHUNK_MAX_CHARACTERS", "1000")),
    )
    chunk_overlap_characters: int = Field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP_CHARACTERS", "100")),
    )
    embedding_vector_size: int = Field(
        default_factory=lambda: int(os.getenv("EMBEDDING_VECTOR_SIZE", "8")),
    )
    qdrant_url: str = Field(
        default_factory=lambda: os.getenv("QDRANT_URL", "http://qdrant:6333"),
    )
    qdrant_collection: str = Field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION", "docsearch_chunks"),
    )
    llm_base_url: str = Field(
        default_factory=lambda: os.getenv("LLM_BASE_URL", "http://llm:8000/v1"),
    )
    llm_model: str = Field(
        default_factory=lambda: os.getenv("LLM_MODEL", "google/gemma-4-E4B-it"),
    )
    llm_api_key: str | None = Field(
        default_factory=lambda: _optional_env("LLM_API_KEY"),
    )
    llm_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0")),
    )
    llm_max_tokens: int = Field(
        default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "1024")),
    )
    llm_temperature: float = Field(
        default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.2")),
    )
    chat_retrieval_limit: int = Field(
        default_factory=lambda: int(os.getenv("CHAT_RETRIEVAL_LIMIT", "5")),
    )
    chat_rerank_top_k: int = Field(
        default_factory=lambda: int(os.getenv("CHAT_RERANK_TOP_K", "5")),
    )
    reranker_backend: str = Field(
        default_factory=lambda: os.getenv("RERANKER_BACKEND", "score"),
    )
    reranker_base_url: str = Field(
        default_factory=lambda: os.getenv("RERANKER_BASE_URL", "http://reranker:8001/v1"),
    )
    reranker_model: str = Field(
        default_factory=lambda: os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"),
    )
    reranker_api_key: str | None = Field(
        default_factory=lambda: _optional_env("RERANKER_API_KEY"),
    )
    reranker_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("RERANKER_TIMEOUT_SECONDS", "10.0")),
    )
    audit_log_backend: str = Field(
        default_factory=lambda: os.getenv("AUDIT_LOG_BACKEND", "inmemory"),
    )
    document_metadata_backend: str = Field(
        default_factory=lambda: os.getenv("DOCUMENT_METADATA_BACKEND", "inmemory"),
    )
    dependency_health_checks_enabled: bool = Field(
        default_factory=lambda: _bool_env(
            "DEPENDENCY_HEALTH_CHECKS_ENABLED",
            _is_production_env(),
        ),
    )
    dependency_health_timeout_seconds: float = Field(
        default_factory=lambda: float(
            os.getenv("DEPENDENCY_HEALTH_TIMEOUT_SECONDS", "2.0"),
        ),
        gt=0,
    )
    rate_limit_enabled: bool = Field(
        default_factory=lambda: _bool_env("RATE_LIMIT_ENABLED", _is_production_env()),
    )
    rate_limit_backend: Literal["memory", "redis"] = Field(
        default_factory=lambda: os.getenv("RATE_LIMIT_BACKEND", "memory"),
    )
    rate_limit_requests: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_REQUESTS", "120")),
        gt=0,
    )
    rate_limit_window_seconds: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
        gt=0,
    )
    rate_limit_redis_prefix: str = Field(
        default_factory=lambda: os.getenv(
            "RATE_LIMIT_REDIS_PREFIX",
            "docsearch:rate-limit",
        ),
    )
    rate_limit_fail_open: bool = Field(
        default_factory=lambda: _bool_env("RATE_LIMIT_FAIL_OPEN", True),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

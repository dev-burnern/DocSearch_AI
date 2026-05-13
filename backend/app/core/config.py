from functools import lru_cache
import os

from pydantic import BaseModel, Field


def _bool_env(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() == "true"


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
            "local-dev-key|local-workspace|Local Workspace",
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

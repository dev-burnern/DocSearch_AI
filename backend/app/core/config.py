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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

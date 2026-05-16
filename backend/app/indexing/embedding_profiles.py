from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

from backend.app.core.config import get_settings

if TYPE_CHECKING:
    from backend.app.core.config import Settings


DEFAULT_EMBEDDING_BASE_URL = "http://embedding:8002/v1"
DEFAULT_BGE_M3_MODEL = "BAAI/bge-m3"


class EmbeddingProfile(BaseModel):
    provider: Literal["bge"] = "bge"
    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: float = Field(gt=0)
    vector_size: int = Field(gt=0)

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("api_key", mode="before")
    @classmethod
    def normalize_api_key(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        return value


def get_default_embedding_profile(
    settings: "Settings | None" = None,
) -> EmbeddingProfile:
    settings = settings or get_settings()
    return EmbeddingProfile(
        provider="bge",
        base_url=settings.embedding_base_url,
        model=settings.embedding_model,
        api_key=settings.embedding_api_key,
        timeout_seconds=settings.embedding_timeout_seconds,
        vector_size=settings.embedding_vector_size,
    )

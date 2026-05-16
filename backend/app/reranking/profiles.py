from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

from backend.app.core.config import get_settings

if TYPE_CHECKING:
    from backend.app.core.config import Settings


DEFAULT_RERANKER_BASE_URL = "http://reranker:8001/v1"
DEFAULT_BGE_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


class RerankerProfile(BaseModel):
    provider: Literal["bge"] = "bge"
    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: float = Field(gt=0)

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


def get_default_reranker_profile(settings: "Settings | None" = None) -> RerankerProfile:
    settings = settings or get_settings()
    return RerankerProfile(
        provider="bge",
        base_url=settings.reranker_base_url,
        model=settings.reranker_model,
        api_key=settings.reranker_api_key,
        timeout_seconds=settings.reranker_timeout_seconds,
    )

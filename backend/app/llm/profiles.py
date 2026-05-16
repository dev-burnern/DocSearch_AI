from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

from backend.app.core.config import get_settings

if TYPE_CHECKING:
    from backend.app.core.config import Settings


DEFAULT_LLM_BASE_URL = "http://llm:8000/v1"
DEFAULT_GEMMA_4_MODEL = "google/gemma-4-E4B-it"


class LLMProfile(BaseModel):
    provider: Literal["vllm"] = "vllm"
    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: float = Field(gt=0)
    max_tokens: int = Field(gt=0)
    temperature: float = Field(ge=0)
    max_retries: int = Field(ge=0)
    retry_backoff_seconds: float = Field(ge=0)

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


def get_default_llm_profile(settings: "Settings | None" = None) -> LLMProfile:
    settings = settings or get_settings()
    return LLMProfile(
        provider="vllm",
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
        max_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
        max_retries=settings.llm_max_retries,
        retry_backoff_seconds=settings.llm_retry_backoff_seconds,
    )

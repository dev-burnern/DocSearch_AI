from functools import lru_cache
import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = Field(
        default_factory=lambda: os.getenv("APP_NAME", "DocSearch AI"),
    )
    app_env: str = Field(
        default_factory=lambda: os.getenv("APP_ENV", "development"),
    )
    debug: bool = Field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true",
    )
    api_keys: str = Field(
        default_factory=lambda: os.getenv(
            "DOCSEARCH_API_KEYS",
            "local-dev-key|local-workspace|Local Workspace",
        ),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

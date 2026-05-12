from fastapi import FastAPI

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "healthy",
            "service": "docsearch-ai-v2",
        }

    @app.get("/ready")
    async def ready() -> dict[str, str]:
        return {
            "status": "ready",
            "service": "docsearch-ai-v2",
        }

    return app


app = create_app()

from fastapi import Depends, FastAPI
from backend.app.auth.dependencies import require_workspace_context
from backend.app.auth.models import WorkspaceContext
from backend.app.middleware.request_context import RequestContextMiddleware

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )
    app.add_middleware(RequestContextMiddleware)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "healthy",
            "service": "docsearch-ai",
        }

    @app.get("/ready")
    async def ready() -> dict[str, str]:
        return {
            "status": "ready",
            "service": "docsearch-ai",
        }

    @app.get("/v1/workspace")
    async def workspace(
        workspace_context: WorkspaceContext = Depends(require_workspace_context),
    ) -> dict[str, str]:
        return workspace_context.model_dump()

    return app


app = create_app()

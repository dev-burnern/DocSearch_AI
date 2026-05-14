from fastapi import Depends, FastAPI
from backend.app.audit.router import router as audit_router
from backend.app.auth.dependencies import require_workspace_context
from backend.app.auth.models import WorkspaceContext
from backend.app.chat.router import router as chat_router
from backend.app.documents.router import router as documents_router
from backend.app.middleware.request_context import RequestContextMiddleware
from backend.app.search.router import router as search_router

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

    app.include_router(documents_router)
    app.include_router(search_router)
    app.include_router(chat_router)
    app.include_router(audit_router)

    return app


app = create_app()

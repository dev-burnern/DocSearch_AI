from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from backend.app.admin.operations import router as admin_operations_router
from backend.app.audit.router import router as audit_router
from backend.app.auth.dependencies import require_workspace_context
from backend.app.auth.models import WorkspaceContext
from backend.app.auth.router import router as auth_router
from backend.app.auth.service import AuthService
from backend.app.auth.store import create_auth_user_store
from backend.app.chat.router import router as chat_router
from backend.app.core.dependency_health import DependencyHealthChecker
from backend.app.core.operation_events import InMemoryOperationEventStore
from backend.app.core.operations import build_readiness_response
from backend.app.core.operations import record_dependency_failure_events
from backend.app.documents.router import router as documents_router
from backend.app.middleware.rate_limit import RateLimitMiddleware
from backend.app.middleware.request_context import RequestContextMiddleware
from backend.app.middleware.security_headers import SecurityHeadersMiddleware
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
    app.add_middleware(RateLimitMiddleware, settings=settings)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.state.auth_service = AuthService(
        settings,
        user_store=create_auth_user_store(settings),
    )
    app.state.dependency_health_checker = DependencyHealthChecker()
    app.state.operation_event_store = InMemoryOperationEventStore()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "healthy",
            "service": "docsearch-ai",
        }

    @app.get("/ready")
    async def ready() -> JSONResponse:
        readiness = build_readiness_response(
            settings,
            dependency_health_checker=app.state.dependency_health_checker,
        )
        record_dependency_failure_events(
            checks=readiness.checks,
            event_store=app.state.operation_event_store,
        )
        status_code = 200 if readiness.status == "ready" else 503
        return JSONResponse(
            status_code=status_code,
            content=readiness.model_dump(),
        )

    @app.get("/v1/workspace")
    async def workspace(
        workspace_context: WorkspaceContext = Depends(require_workspace_context),
    ) -> WorkspaceContext:
        return workspace_context

    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(search_router)
    app.include_router(chat_router)
    app.include_router(audit_router)
    app.include_router(admin_operations_router)

    return app


app = create_app()

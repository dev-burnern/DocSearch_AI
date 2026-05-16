from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from backend.app.auth.dependencies import require_admin_workspace_context
from backend.app.auth.models import UserRole, WorkspaceContext
from backend.app.core.config import Settings, get_settings
from backend.app.core.operation_events import OperationEvent
from backend.app.core.operations import OperationalCheck, OperationalStatus
from backend.app.core.operations import build_readiness_response
from backend.app.core.operations import record_dependency_failure_events


router = APIRouter(prefix="/v1/admin", tags=["admin"])


class OperationsWorkspaceSummary(BaseModel):
    workspace_id: str
    workspace_name: str
    role: UserRole


class RateLimitSettingsSummary(BaseModel):
    enabled: bool
    backend: str
    requests: int
    window_seconds: int
    fail_open: bool


class BackendSettingsSummary(BaseModel):
    audit_log: str
    document_metadata: str
    indexing_queue: str
    reranker: str


class ModelSettingsSummary(BaseModel):
    llm: str
    reranker: str
    embedding_vector_size: int


class OperationsSettingsSummary(BaseModel):
    environment: str
    debug: bool
    dependency_health_checks_enabled: bool
    dependency_health_timeout_seconds: float
    rate_limit: RateLimitSettingsSummary
    backends: BackendSettingsSummary
    models: ModelSettingsSummary


class OperationsStatusResponse(BaseModel):
    status: OperationalStatus
    service: str
    workspace: OperationsWorkspaceSummary
    checks: list[OperationalCheck]
    events: list[OperationEvent]
    settings: OperationsSettingsSummary


@router.get("/operations", response_model=OperationsStatusResponse)
async def get_operations_status(
    request: Request,
    workspace_context: WorkspaceContext = Depends(require_admin_workspace_context),
    settings: Settings = Depends(get_settings),
) -> OperationsStatusResponse:
    readiness = build_readiness_response(
        settings,
        dependency_health_checker=request.app.state.dependency_health_checker,
    )
    event_store = request.app.state.operation_event_store
    record_dependency_failure_events(
        checks=readiness.checks,
        event_store=event_store,
    )
    return OperationsStatusResponse(
        status=readiness.status,
        service=readiness.service,
        workspace=OperationsWorkspaceSummary(
            workspace_id=workspace_context.workspace_id,
            workspace_name=workspace_context.workspace_name,
            role=workspace_context.role,
        ),
        checks=readiness.checks,
        events=event_store.list_events(),
        settings=_build_settings_summary(settings),
    )


def _build_settings_summary(settings: Settings) -> OperationsSettingsSummary:
    return OperationsSettingsSummary(
        environment=settings.app_env,
        debug=settings.debug,
        dependency_health_checks_enabled=settings.dependency_health_checks_enabled,
        dependency_health_timeout_seconds=settings.dependency_health_timeout_seconds,
        rate_limit=RateLimitSettingsSummary(
            enabled=settings.rate_limit_enabled,
            backend=settings.rate_limit_backend,
            requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
            fail_open=settings.rate_limit_fail_open,
        ),
        backends=BackendSettingsSummary(
            audit_log=settings.audit_log_backend,
            document_metadata=settings.document_metadata_backend,
            indexing_queue=settings.indexing_queue_backend,
            reranker=settings.reranker_backend,
        ),
        models=ModelSettingsSummary(
            llm=settings.llm_model,
            reranker=settings.reranker_model,
            embedding_vector_size=settings.embedding_vector_size,
        ),
    )

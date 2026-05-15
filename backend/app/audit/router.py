from datetime import UTC, datetime
from functools import lru_cache
from typing import Callable

from fastapi import APIRouter, Depends, Query, Response

from backend.app.audit.export import build_chat_audit_csv
from backend.app.audit.models import ChatAuditEventFilters, ChatAuditEventListResponse
from backend.app.audit.postgres_store import PostgresAuditLogStore
from backend.app.audit.store import AuditLogStore, InMemoryAuditLogStore
from backend.app.auth.dependencies import require_workspace_context
from backend.app.auth.models import WorkspaceContext
from backend.app.core.config import Settings, get_settings


router = APIRouter(prefix="/v1/audit-logs", tags=["audit"])


def create_audit_log_store(
    settings: Settings,
    *,
    connection_factory: Callable[[], object] | None = None,
) -> AuditLogStore:
    if settings.audit_log_backend == "postgres":
        return PostgresAuditLogStore(
            database_url=settings.database_url,
            connection_factory=connection_factory,
        )

    return InMemoryAuditLogStore()


@lru_cache(maxsize=1)
def get_audit_log_store() -> AuditLogStore:
    return create_audit_log_store(get_settings())


@router.get("/chat", response_model=ChatAuditEventListResponse)
async def list_chat_audit_events(
    query: str | None = Query(default=None),
    document_id: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    occurred_from: datetime | None = Query(default=None, alias="from"),
    occurred_to: datetime | None = Query(default=None, alias="to"),
    limit: int = Query(default=100, ge=1, le=200),
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
    audit_log: AuditLogStore = Depends(get_audit_log_store),
) -> ChatAuditEventListResponse:
    filters = _build_chat_audit_filters(
        query=query,
        document_id=document_id,
        request_id=request_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=limit,
    )
    events = audit_log.list_chat_events(
        workspace_id=workspace_context.workspace_id,
        filters=filters,
    )
    return ChatAuditEventListResponse(events=events, total=len(events))


@router.get("/chat/export")
async def export_chat_audit_events(
    query: str | None = Query(default=None),
    document_id: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    occurred_from: datetime | None = Query(default=None, alias="from"),
    occurred_to: datetime | None = Query(default=None, alias="to"),
    limit: int = Query(default=100, ge=1, le=200),
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
    audit_log: AuditLogStore = Depends(get_audit_log_store),
) -> Response:
    filters = _build_chat_audit_filters(
        query=query,
        document_id=document_id,
        request_id=request_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=limit,
    )
    events = audit_log.list_chat_events(
        workspace_id=workspace_context.workspace_id,
        filters=filters,
    )
    filename = f"chat-audit-logs-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.csv"
    return Response(
        content=build_chat_audit_csv(events),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


def _build_chat_audit_filters(
    *,
    query: str | None,
    document_id: str | None,
    request_id: str | None,
    occurred_from: datetime | None,
    occurred_to: datetime | None,
    limit: int,
) -> ChatAuditEventFilters:
    return ChatAuditEventFilters(
        query=query,
        document_id=document_id,
        request_id=request_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=limit,
    )

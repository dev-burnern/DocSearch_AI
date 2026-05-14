from functools import lru_cache
from typing import Callable

from fastapi import APIRouter, Depends

from backend.app.audit.models import ChatAuditEventListResponse
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
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
    audit_log: AuditLogStore = Depends(get_audit_log_store),
) -> ChatAuditEventListResponse:
    events = audit_log.list_chat_events(
        workspace_id=workspace_context.workspace_id,
    )
    return ChatAuditEventListResponse(events=events, total=len(events))

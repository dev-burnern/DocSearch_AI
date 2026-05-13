from functools import lru_cache

from fastapi import APIRouter, Depends

from backend.app.audit.models import ChatAuditEventListResponse
from backend.app.audit.store import AuditLogStore, InMemoryAuditLogStore
from backend.app.auth.dependencies import require_workspace_context
from backend.app.auth.models import WorkspaceContext


router = APIRouter(prefix="/v1/audit-logs", tags=["audit"])


@lru_cache(maxsize=1)
def get_audit_log_store() -> AuditLogStore:
    return InMemoryAuditLogStore()


@router.get("/chat", response_model=ChatAuditEventListResponse)
async def list_chat_audit_events(
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
    audit_log: AuditLogStore = Depends(get_audit_log_store),
) -> ChatAuditEventListResponse:
    events = audit_log.list_chat_events(
        workspace_id=workspace_context.workspace_id,
    )
    return ChatAuditEventListResponse(events=events, total=len(events))

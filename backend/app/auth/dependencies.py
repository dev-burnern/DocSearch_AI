from fastapi import Depends, HTTPException, Request, status

from backend.app.auth.models import ADMIN_ROLE, WorkspaceContext
from backend.app.auth.service import AuthService
from backend.app.core.config import get_settings


def get_auth_service() -> AuthService:
    return AuthService(get_settings())


def require_workspace_context(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> WorkspaceContext:
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_MISSING_API_KEY",
                "message": "API key is required.",
            },
        )

    record = auth_service.validate_api_key(api_key)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_INVALID_API_KEY",
                "message": "API key is invalid.",
            },
        )

    request.state.request_context.workspace_id = record.workspace_id
    request.state.request_context.workspace_name = record.workspace_name

    return WorkspaceContext(
        request_id=request.state.request_context.request_id,
        workspace_id=record.workspace_id,
        workspace_name=record.workspace_name,
        role=record.role,
    )


def require_admin_workspace_context(
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
) -> WorkspaceContext:
    if workspace_context.role != ADMIN_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTH_FORBIDDEN_ROLE",
                "message": "Admin role is required.",
            },
        )

    return workspace_context

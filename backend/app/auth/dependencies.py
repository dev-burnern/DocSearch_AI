from fastapi import Depends, HTTPException, Request, status

from backend.app.auth.models import ADMIN_ROLE, ApiKeyRecord, UserRecord, WorkspaceContext
from backend.app.auth.service import AuthService


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def require_workspace_context(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> WorkspaceContext:
    api_key = request.headers.get("X-API-Key")
    if api_key:
        record = auth_service.validate_api_key(api_key)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "AUTH_INVALID_API_KEY",
                    "message": "API key is invalid.",
                },
            )
        return _context_from_api_key(request, record)

    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_MISSING_CREDENTIALS",
                "message": "Authentication credential is required.",
            },
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_INVALID_TOKEN",
                "message": "Bearer token is required.",
            },
        )

    try:
        record = auth_service.validate_access_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_INVALID_TOKEN",
                "message": str(exc),
            },
        ) from exc

    return _context_from_user(request, record)


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


def _context_from_api_key(request: Request, record: ApiKeyRecord) -> WorkspaceContext:
    request.state.request_context.workspace_id = record.workspace_id
    request.state.request_context.workspace_name = record.workspace_name

    return WorkspaceContext(
        request_id=request.state.request_context.request_id,
        workspace_id=record.workspace_id,
        workspace_name=record.workspace_name,
        role=record.role,
    )


def _context_from_user(request: Request, record: UserRecord) -> WorkspaceContext:
    request.state.request_context.workspace_id = record.workspace_id
    request.state.request_context.workspace_name = record.workspace_name

    return WorkspaceContext(
        request_id=request.state.request_context.request_id,
        workspace_id=record.workspace_id,
        workspace_name=record.workspace_name,
        role=record.role,
        employee_id=record.employee_id,
        display_name=record.display_name,
    )

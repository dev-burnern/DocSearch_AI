from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.app.auth.dependencies import get_auth_service, require_workspace_context
from backend.app.auth.models import AuthResponse, LoginRequest, SignupRequest, WorkspaceContext
from backend.app.auth.service import (
    AuthError,
    AuthService,
    DuplicateUserError,
    InvalidCredentialsError,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request_body: SignupRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        user = auth_service.register_user(
            employee_id=request_body.employee_id,
            password=request_body.password,
            display_name=request_body.display_name,
        )
    except DuplicateUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "AUTH_DUPLICATE_EMPLOYEE_ID", "message": str(exc)},
        ) from exc
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "AUTH_INVALID_SIGNUP", "message": str(exc)},
        ) from exc

    return _build_auth_response(request, auth_service, user)


@router.post("/login", response_model=AuthResponse)
async def login(
    request_body: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        user = auth_service.authenticate_user(
            employee_id=request_body.employee_id,
            password=request_body.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_INVALID_CREDENTIALS", "message": str(exc)},
        ) from exc

    return _build_auth_response(request, auth_service, user)


@router.get("/me", response_model=WorkspaceContext)
async def me(
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
) -> WorkspaceContext:
    return workspace_context


def _build_auth_response(request: Request, auth_service: AuthService, user) -> AuthResponse:
    workspace = WorkspaceContext(
        request_id=request.state.request_context.request_id,
        workspace_id=user.workspace_id,
        workspace_name=user.workspace_name,
        role=user.role,
        employee_id=user.employee_id,
        display_name=user.display_name,
    )
    return AuthResponse(
        access_token=auth_service.create_access_token(user),
        workspace=workspace,
    )

from pydantic import BaseModel


UserRole = str
MEMBER_ROLE = "member"
ADMIN_ROLE = "admin"
SUPPORTED_ROLES = {MEMBER_ROLE, ADMIN_ROLE}


class ApiKeyRecord(BaseModel):
    api_key: str
    workspace_id: str
    workspace_name: str
    role: UserRole = MEMBER_ROLE


class UserRecord(BaseModel):
    employee_id: str
    password_hash: str
    workspace_id: str
    workspace_name: str
    role: UserRole = MEMBER_ROLE
    display_name: str | None = None


class WorkspaceContext(BaseModel):
    request_id: str
    workspace_id: str
    workspace_name: str
    role: UserRole = MEMBER_ROLE
    employee_id: str | None = None
    display_name: str | None = None


class LoginRequest(BaseModel):
    employee_id: str
    password: str


class SignupRequest(BaseModel):
    employee_id: str
    password: str
    display_name: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    workspace: WorkspaceContext

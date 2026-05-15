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


class WorkspaceContext(BaseModel):
    request_id: str
    workspace_id: str
    workspace_name: str
    role: UserRole = MEMBER_ROLE

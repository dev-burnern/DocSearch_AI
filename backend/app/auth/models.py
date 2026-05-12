from pydantic import BaseModel


class ApiKeyRecord(BaseModel):
    api_key: str
    workspace_id: str
    workspace_name: str


class WorkspaceContext(BaseModel):
    request_id: str
    workspace_id: str
    workspace_name: str

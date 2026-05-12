from dataclasses import dataclass
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


@dataclass
class RequestContextState:
    request_id: str
    workspace_id: str | None = None
    workspace_name: str | None = None


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_context = RequestContextState(
            request_id=f"req_{uuid.uuid4().hex}",
        )

        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_context.request_id
        return response

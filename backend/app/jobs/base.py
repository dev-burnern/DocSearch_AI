from dataclasses import dataclass
from typing import Literal, Protocol


JobStatus = Literal["queued", "processing", "completed", "failed"]


@dataclass(frozen=True)
class IndexDocumentJob:
    job_id: str
    workspace_id: str
    workspace_name: str
    document_id: str
    filename: str
    content_type: str
    storage_key: str
    attempt: int = 1
    max_attempts: int = 3


@dataclass(frozen=True)
class JobDispatchResult:
    job_id: str
    status: JobStatus
    chunk_count: int = 0
    failure_reason: str | None = None


class JobQueue(Protocol):
    def enqueue(self, job: IndexDocumentJob) -> JobDispatchResult:
        ...

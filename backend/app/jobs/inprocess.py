from collections.abc import Callable

from backend.app.indexing.pipeline import IndexingResult
from backend.app.jobs.base import IndexDocumentJob, JobDispatchResult


class InProcessJobQueue:
    def __init__(
        self,
        *,
        processor: Callable[[IndexDocumentJob], IndexingResult],
    ) -> None:
        self._processor = processor

    def enqueue(self, job: IndexDocumentJob) -> JobDispatchResult:
        result = self._processor(job)
        return JobDispatchResult(
            job_id=job.job_id,
            status="completed",
            chunk_count=result.chunk_count,
        )

import json

from backend.app.jobs.base import IndexDocumentJob, JobDispatchResult


class RedisJobQueue:
    def enqueue(self, job: IndexDocumentJob) -> JobDispatchResult:
        self.serialize(job)
        return JobDispatchResult(
            job_id=job.job_id,
            status="queued",
            chunk_count=0,
        )

    @staticmethod
    def serialize(job: IndexDocumentJob) -> str:
        return json.dumps(
            {
                "job_id": job.job_id,
                "workspace_id": job.workspace_id,
                "workspace_name": job.workspace_name,
                "document_id": job.document_id,
                "filename": job.filename,
                "content_type": job.content_type,
                "storage_key": job.storage_key,
            },
        )

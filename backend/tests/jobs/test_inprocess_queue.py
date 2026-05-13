def test_인프로세스_큐가_잡을_즉시_처리한다() -> None:
    from backend.app.indexing.pipeline import IndexingResult
    from backend.app.jobs.base import IndexDocumentJob
    from backend.app.jobs.inprocess import InProcessJobQueue

    handled_jobs: list[str] = []

    def process(job: IndexDocumentJob) -> IndexingResult:
        handled_jobs.append(job.job_id)
        return IndexingResult(
            job_id=job.job_id,
            document_id=job.document_id,
            parser="text",
            chunk_count=2,
            chunks=["alpha", "beta"],
            embeddings=[[0.1, 0.2, 0.3, 0.4], [0.2, 0.3, 0.4, 0.5]],
            embedding_count=2,
            embedding_dimensions=4,
        )

    queue = InProcessJobQueue(processor=process)
    result = queue.enqueue(
        IndexDocumentJob(
            job_id="job-1",
            workspace_id="workspace-alpha",
            workspace_name="Workspace Alpha",
            document_id="doc-1",
            filename="memo.txt",
            content_type="text/plain",
            storage_key="workspace-alpha/doc-1/memo.txt",
        ),
    )

    assert handled_jobs == ["job-1"]
    assert result.job_id == "job-1"
    assert result.status == "completed"
    assert result.chunk_count == 2

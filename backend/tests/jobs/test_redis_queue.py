from backend.app.core.operation_events import InMemoryOperationEventStore
from backend.app.jobs.base import IndexDocumentJob
from backend.app.jobs.redis_queue import RedisJobQueue
from redis.exceptions import TimeoutError as RedisTimeoutError


def test_redis_job_queue_pushes_serialized_job_with_retry_policy() -> None:
    redis_client = FakeRedisClient()
    queue = RedisJobQueue(
        redis_client=redis_client,
        queue_key="docsearch:indexing:test",
        max_attempts=5,
    )
    job = _job()

    result = queue.enqueue(job)

    assert result.job_id == "job-1"
    assert result.status == "queued"
    assert redis_client.pushed == [("docsearch:indexing:test", redis_client.payload)]
    queued = RedisJobQueue.deserialize(redis_client.payload)
    assert queued.job_id == "job-1"
    assert queued.attempt == 1
    assert queued.max_attempts == 5


def test_redis_job_queue_pops_serialized_job() -> None:
    redis_client = FakeRedisClient(payload=RedisJobQueue.serialize(_job()))
    queue = RedisJobQueue(
        redis_client=redis_client,
        queue_key="docsearch:indexing:test",
    )

    job = queue.pop(timeout_seconds=1)

    assert job == _job()
    assert redis_client.pop_calls == [
        {"queue_key": "docsearch:indexing:test", "timeout": 1}
    ]


def test_redis_job_queue_treats_idle_timeout_as_empty_pop() -> None:
    redis_client = TimeoutRedisClient()
    queue = RedisJobQueue(
        redis_client=redis_client,
        queue_key="docsearch:indexing:test",
    )

    job = queue.pop(timeout_seconds=1)

    assert job is None
    assert redis_client.pop_calls == [
        {"queue_key": "docsearch:indexing:test", "timeout": 1}
    ]


def test_redis_job_queue_reports_pending_count() -> None:
    redis_client = FakeRedisClient(pending_count=4)
    queue = RedisJobQueue(
        redis_client=redis_client,
        queue_key="docsearch:indexing:test",
    )

    assert queue.pending_count() == 4
    assert redis_client.length_calls == ["docsearch:indexing:test"]


def test_redis_job_queue_records_enqueue_failure_event() -> None:
    event_store = InMemoryOperationEventStore()
    queue = RedisJobQueue(
        redis_client=FailingRedisClient(),
        queue_key="docsearch:indexing:test",
        operation_event_store=event_store,
    )

    result = queue.enqueue(_job())

    assert result.status == "failed"
    assert result.failure_reason == "redis unavailable"
    event = event_store.list_events()[0]
    assert event.event_type == "indexing.queue_unavailable"
    assert event.severity == "error"
    assert event.source == "indexing"
    assert event.details == {
        "job_id": "job-1",
        "workspace_id": "workspace-alpha",
        "document_id": "doc-1",
        "filename": "memo.txt",
    }


def _job() -> IndexDocumentJob:
    return IndexDocumentJob(
        job_id="job-1",
        workspace_id="workspace-alpha",
        workspace_name="Workspace Alpha",
        document_id="doc-1",
        filename="memo.txt",
        content_type="text/plain",
        storage_key="workspace-alpha/doc-1/memo.txt",
    )


class FakeRedisClient:
    def __init__(
        self,
        *,
        payload: str | None = None,
        pending_count: int = 0,
    ) -> None:
        self.payload = payload or ""
        self.pending_count = pending_count
        self.pushed: list[tuple[str, str]] = []
        self.pop_calls: list[dict[str, object]] = []
        self.length_calls: list[str] = []

    def rpush(self, queue_key: str, payload: str) -> None:
        self.payload = payload
        self.pushed.append((queue_key, payload))

    def brpop(self, queue_key: str, *, timeout: int):
        self.pop_calls.append({"queue_key": queue_key, "timeout": timeout})
        if not self.payload:
            return None
        return queue_key, self.payload

    def llen(self, queue_key: str) -> int:
        self.length_calls.append(queue_key)
        return self.pending_count


class FailingRedisClient:
    def rpush(self, queue_key: str, payload: str) -> None:
        raise RuntimeError("redis unavailable")


class TimeoutRedisClient:
    def __init__(self) -> None:
        self.pop_calls: list[dict[str, object]] = []

    def brpop(self, queue_key: str, *, timeout: int):
        self.pop_calls.append({"queue_key": queue_key, "timeout": timeout})
        raise RedisTimeoutError("Timeout reading from socket")

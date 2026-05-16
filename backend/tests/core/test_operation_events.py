from backend.app.core.operation_events import (
    InMemoryOperationEventStore,
    OperationEvent,
)


def test_inmemory_operation_event_store_returns_recent_events_first() -> None:
    store = InMemoryOperationEventStore(max_events=2)

    first = OperationEvent(
        event_type="dependency.health_failed",
        severity="error",
        source="qdrant",
        message="Qdrant 연결에 실패했습니다.",
    )
    second = OperationEvent(
        event_type="rate_limit.backend_unavailable",
        severity="error",
        source="rate_limit",
        message="Redis rate limit backend is unavailable.",
    )
    third = OperationEvent(
        event_type="dependency.health_failed",
        severity="error",
        source="minio",
        message="MinIO 연결에 실패했습니다.",
    )

    store.record(first)
    store.record(second)
    store.record(third)

    events = store.list_events()

    assert [event.event_id for event in events] == [
        third.event_id,
        second.event_id,
    ]

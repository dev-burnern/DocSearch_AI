from backend.app.audit.router import create_audit_log_store
from backend.app.audit.store import InMemoryAuditLogStore
from backend.app.core.config import Settings


class FakeConnection:
    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def execute(self, sql: str, params=None):
        return self

    def commit(self) -> None:
        return None


def test_감사로그_저장소_factory가_inmemory_기본값을_사용한다() -> None:
    store = create_audit_log_store(Settings())

    assert isinstance(store, InMemoryAuditLogStore)


def test_감사로그_저장소_factory가_postgres_설정을_반영한다() -> None:
    store = create_audit_log_store(
        Settings(
            audit_log_backend="postgres",
            database_url="postgresql://docsearch:docsearch@postgres:5432/docsearch",
        ),
        connection_factory=lambda: FakeConnection(),
    )

    assert store.__class__.__name__ == "PostgresAuditLogStore"

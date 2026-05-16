from backend.app.auth.models import UserRecord
from backend.app.auth.postgres_store import PostgresAuthUserStore
from backend.app.auth.store import parse_auth_users


class FakeCursor:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows


class FakeConnection:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self.rows = rows or []
        self.statements: list[tuple[str, dict[str, object] | None]] = []
        self.commit_count = 0

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def execute(
        self,
        sql: str,
        params: dict[str, object] | None = None,
    ) -> FakeCursor:
        self.statements.append((sql, params))
        return FakeCursor(self.rows)

    def commit(self) -> None:
        self.commit_count += 1


def test_PostgresAuthUserStore는_스키마를_보장하고_기본_계정을_시드한다() -> None:
    connection = FakeConnection()
    store = PostgresAuthUserStore(
        database_url="postgresql://docsearch:docsearch@postgres:5432/docsearch",
        seed_users=parse_auth_users(
            "2301029|password|local-workspace|Local Workspace|admin|관리자",
        ),
        connection_factory=lambda: connection,
    )

    assert store is not None
    assert "CREATE TABLE IF NOT EXISTS auth_users" in connection.statements[0][0]
    seed_sql, seed_params = connection.statements[-1]
    assert "INSERT INTO auth_users" in seed_sql
    assert "ON CONFLICT (employee_id) DO NOTHING" in seed_sql
    assert seed_params is not None
    assert seed_params["employee_id"] == "2301029"
    assert seed_params["role"] == "admin"
    assert seed_params["display_name"] == "관리자"
    assert connection.commit_count == 2


def test_PostgresAuthUserStore는_회원가입_계정을_저장한다() -> None:
    connection = FakeConnection(rows=[{"employee_id": "2001"}])
    store = PostgresAuthUserStore(
        database_url="postgresql://docsearch:docsearch@postgres:5432/docsearch",
        seed_users=[],
        connection_factory=lambda: connection,
    )

    created = store.create_user(
        UserRecord(
            employee_id="2001",
            password_hash="pbkdf2_sha256$salt$digest",
            workspace_id="local-workspace",
            workspace_name="Local Workspace",
            role="member",
            display_name="사용자",
        ),
    )

    assert created is True
    insert_sql, insert_params = connection.statements[-1]
    assert "RETURNING employee_id" in insert_sql
    assert insert_params is not None
    assert insert_params["employee_id"] == "2001"
    assert insert_params["role"] == "member"
    assert connection.commit_count == 2


def test_PostgresAuthUserStore는_사번으로_계정을_조회한다() -> None:
    row = {
        "employee_id": "2301029",
        "password_hash": "pbkdf2_sha256$salt$digest",
        "workspace_id": "local-workspace",
        "workspace_name": "Local Workspace",
        "role": "admin",
        "display_name": "관리자",
    }
    connection = FakeConnection(rows=[row])
    store = PostgresAuthUserStore(
        database_url="postgresql://docsearch:docsearch@postgres:5432/docsearch",
        seed_users=[],
        connection_factory=lambda: connection,
    )

    record = store.get_user("2301029")

    assert record == UserRecord(**row)
    select_sql, select_params = connection.statements[-1]
    assert "FROM auth_users" in select_sql
    assert "WHERE employee_id = %(employee_id)s" in select_sql
    assert select_params == {"employee_id": "2301029"}

from __future__ import annotations

from typing import Callable, Iterable

from backend.app.auth.models import UserRecord


class PostgresAuthUserStore:
    def __init__(
        self,
        *,
        database_url: str,
        seed_users: Iterable[UserRecord],
        connection_factory: Callable[[], object] | None = None,
    ) -> None:
        self._database_url = database_url
        self._seed_users = list(seed_users)
        self._connection_factory = connection_factory or self._create_connection
        self._ensure_schema()
        self._seed_default_users()

    def get_user(self, employee_id: str) -> UserRecord | None:
        with self._connection_factory() as connection:
            cursor = connection.execute(
                f"""
                SELECT
                    {_user_columns()}
                FROM auth_users
                WHERE employee_id = %(employee_id)s
                """,
                {"employee_id": employee_id},
            )
            rows = cursor.fetchall()

        if not rows:
            return None
        return UserRecord.model_validate(rows[0])

    def create_user(self, record: UserRecord) -> bool:
        with self._connection_factory() as connection:
            cursor = connection.execute(
                """
                INSERT INTO auth_users (
                    employee_id,
                    password_hash,
                    workspace_id,
                    workspace_name,
                    role,
                    display_name
                )
                VALUES (
                    %(employee_id)s,
                    %(password_hash)s,
                    %(workspace_id)s,
                    %(workspace_name)s,
                    %(role)s,
                    %(display_name)s
                )
                ON CONFLICT (employee_id) DO NOTHING
                RETURNING employee_id
                """,
                record.model_dump(mode="python"),
            )
            rows = cursor.fetchall()
            connection.commit()

        return bool(rows)

    def _ensure_schema(self) -> None:
        with self._connection_factory() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_users (
                    employee_id TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    workspace_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    display_name TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """,
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_auth_users_workspace
                ON auth_users (workspace_id)
                """,
            )
            connection.commit()

    def _seed_default_users(self) -> None:
        if not self._seed_users:
            return

        with self._connection_factory() as connection:
            for record in self._seed_users:
                connection.execute(
                    """
                    INSERT INTO auth_users (
                        employee_id,
                        password_hash,
                        workspace_id,
                        workspace_name,
                        role,
                        display_name
                    )
                    VALUES (
                        %(employee_id)s,
                        %(password_hash)s,
                        %(workspace_id)s,
                        %(workspace_name)s,
                        %(role)s,
                        %(display_name)s
                    )
                    ON CONFLICT (employee_id) DO NOTHING
                    """,
                    record.model_dump(mode="python"),
                )
            connection.commit()

    def _create_connection(self) -> object:
        from psycopg import connect
        from psycopg.rows import dict_row

        return connect(self._database_url, row_factory=dict_row)


def _user_columns() -> str:
    return """
                    employee_id,
                    password_hash,
                    workspace_id,
                    workspace_name,
                    role,
                    display_name
    """

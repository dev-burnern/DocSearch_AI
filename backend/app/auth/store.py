from __future__ import annotations

import hashlib
import secrets
from threading import Lock
from typing import Iterable, Protocol

from backend.app.auth.models import MEMBER_ROLE, SUPPORTED_ROLES, UserRecord


class AuthUserStore(Protocol):
    def get_user(self, employee_id: str) -> UserRecord | None:
        raise NotImplementedError

    def create_user(self, record: UserRecord) -> bool:
        raise NotImplementedError


class InMemoryAuthUserStore:
    def __init__(self, seed_users: Iterable[UserRecord]) -> None:
        self._records = {record.employee_id: record for record in seed_users}
        self._lock = Lock()

    def get_user(self, employee_id: str) -> UserRecord | None:
        with self._lock:
            return self._records.get(employee_id)

    def create_user(self, record: UserRecord) -> bool:
        with self._lock:
            if record.employee_id in self._records:
                return False
            self._records[record.employee_id] = record
            return True


def parse_auth_users(raw_value: str) -> list[UserRecord]:
    records: list[UserRecord] = []

    for entry in raw_value.split(";"):
        normalized_entry = entry.strip()
        if not normalized_entry:
            continue

        parts = [part.strip() for part in normalized_entry.split("|")]
        if len(parts) not in {5, 6}:
            raise ValueError(
                "DOCSEARCH_AUTH_USERS entries must use employee_id|password|workspace_id|workspace_name|role(|display_name) format.",
            )
        role = parts[4]
        if role not in SUPPORTED_ROLES:
            raise ValueError("DOCSEARCH_AUTH_USERS role must be one of: admin, member.")

        employee_id = parts[0].strip()
        if not employee_id:
            raise ValueError("DOCSEARCH_AUTH_USERS employee_id must not be empty.")
        records.append(
            UserRecord(
                employee_id=employee_id,
                password_hash=_hash_password(parts[1]),
                workspace_id=parts[2],
                workspace_name=parts[3],
                role=role,
                display_name=_normalize_optional(parts[5] if len(parts) == 6 else None),
            ),
        )

    return records


def create_auth_user_store(settings) -> AuthUserStore:
    seed_users = parse_auth_users(settings.auth_users)
    if settings.auth_user_backend == "postgres":
        from backend.app.auth.postgres_store import PostgresAuthUserStore

        return PostgresAuthUserStore(
            database_url=settings.database_url,
            seed_users=seed_users,
        )

    return InMemoryAuthUserStore(seed_users)


def build_member_user_record(
    *,
    employee_id: str,
    password_hash: str,
    workspace_id: str,
    workspace_name: str,
    display_name: str | None = None,
) -> UserRecord:
    return UserRecord(
        employee_id=employee_id,
        password_hash=password_hash,
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        role=MEMBER_ROLE,
        display_name=display_name,
    )


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        120_000,
    ).hex()
    return f"pbkdf2_sha256${salt}${digest}"

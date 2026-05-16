from __future__ import annotations

from datetime import UTC, datetime, timedelta
import base64
import hashlib
import hmac
import json
import secrets

from backend.app.auth.models import (
    MEMBER_ROLE,
    SUPPORTED_ROLES,
    ApiKeyRecord,
    UserRecord,
)
from backend.app.auth.store import (
    AuthUserStore,
    InMemoryAuthUserStore,
    build_member_user_record,
    parse_auth_users,
)
from backend.app.core.config import Settings


class AuthError(ValueError):
    pass


class DuplicateUserError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class InvalidTokenError(AuthError):
    pass


class AuthService:
    def __init__(
        self,
        settings: Settings,
        user_store: AuthUserStore | None = None,
    ) -> None:
        self._settings = settings
        self._api_keys: list[ApiKeyRecord] | None = None
        self._user_store = user_store or InMemoryAuthUserStore(
            parse_auth_users(settings.auth_users),
        )

    def validate_api_key(self, api_key: str) -> ApiKeyRecord | None:
        for record in self._get_api_keys():
            if secrets.compare_digest(record.api_key, api_key):
                return record
        return None

    def register_user(
        self,
        *,
        employee_id: str,
        password: str,
        display_name: str | None = None,
    ) -> UserRecord:
        normalized_employee_id = _normalize_employee_id(employee_id)
        _validate_password(password)
        if self._user_store.get_user(normalized_employee_id) is not None:
            raise DuplicateUserError("이미 가입된 사번입니다.")

        record = build_member_user_record(
            employee_id=normalized_employee_id,
            password_hash=hash_password(password),
            workspace_id=self._settings.signup_default_workspace_id,
            workspace_name=self._settings.signup_default_workspace_name,
            display_name=_normalize_optional(display_name),
        )
        if not self._user_store.create_user(record):
            raise DuplicateUserError("이미 가입된 사번입니다.")
        return record

    def authenticate_user(self, *, employee_id: str, password: str) -> UserRecord:
        record = self._user_store.get_user(_normalize_employee_id(employee_id))
        if record is None or not _verify_password(password, record.password_hash):
            raise InvalidCredentialsError("사번 또는 비밀번호가 올바르지 않습니다.")
        return record

    def create_access_token(self, record: UserRecord) -> str:
        expires_at = datetime.now(UTC) + timedelta(
            seconds=self._settings.auth_token_ttl_seconds,
        )
        payload = {
            "employee_id": record.employee_id,
            "workspace_id": record.workspace_id,
            "workspace_name": record.workspace_name,
            "role": record.role,
            "display_name": record.display_name,
            "exp": int(expires_at.timestamp()),
        }
        encoded_payload = _base64url_encode(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(),
        )
        signature = self._sign(encoded_payload)
        return f"{encoded_payload}.{signature}"

    def validate_access_token(self, token: str) -> UserRecord:
        try:
            encoded_payload, signature = token.split(".", 1)
        except ValueError as exc:
            raise InvalidTokenError("로그인 토큰이 올바르지 않습니다.") from exc

        if not hmac.compare_digest(signature, self._sign(encoded_payload)):
            raise InvalidTokenError("로그인 토큰이 올바르지 않습니다.")

        try:
            payload = json.loads(_base64url_decode(encoded_payload))
        except (ValueError, json.JSONDecodeError) as exc:
            raise InvalidTokenError("로그인 토큰이 올바르지 않습니다.") from exc

        expires_at = int(payload.get("exp", 0))
        if expires_at < int(datetime.now(UTC).timestamp()):
            raise InvalidTokenError("로그인이 만료되었습니다.")

        return UserRecord(
            employee_id=str(payload["employee_id"]),
            password_hash="",
            workspace_id=str(payload["workspace_id"]),
            workspace_name=str(payload["workspace_name"]),
            role=str(payload.get("role", MEMBER_ROLE)),
            display_name=payload.get("display_name"),
        )

    def _get_api_keys(self) -> list[ApiKeyRecord]:
        if self._api_keys is None:
            self._api_keys = self._parse_api_keys(self._settings.api_keys)
        return self._api_keys

    def _sign(self, encoded_payload: str) -> str:
        return _base64url_encode(
            hmac.new(
                self._settings.auth_token_secret.encode(),
                encoded_payload.encode(),
                hashlib.sha256,
            ).digest(),
        )

    @staticmethod
    def _parse_api_keys(raw_value: str) -> list[ApiKeyRecord]:
        records: list[ApiKeyRecord] = []

        for entry in raw_value.split(";"):
            normalized_entry = entry.strip()
            if not normalized_entry:
                continue

            parts = [part.strip() for part in normalized_entry.split("|")]
            if len(parts) not in {3, 4}:
                raise ValueError(
                    "DOCSEARCH_API_KEYS entries must use api_key|workspace_id|workspace_name(|role) format.",
                )
            role = parts[3] if len(parts) == 4 else MEMBER_ROLE
            if role not in SUPPORTED_ROLES:
                raise ValueError("DOCSEARCH_API_KEYS role must be one of: admin, member.")

            records.append(
                ApiKeyRecord(
                    api_key=parts[0],
                    workspace_id=parts[1],
                    workspace_name=parts[2],
                    role=role,
                ),
            )

        return records


def _normalize_employee_id(employee_id: str) -> str:
    normalized = employee_id.strip()
    if not normalized:
        raise AuthError("사번을 입력하세요.")
    return normalized


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _validate_password(password: str) -> None:
    if len(password) < 4:
        raise AuthError("비밀번호는 4자 이상이어야 합니다.")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        120_000,
    ).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, salt, expected_digest = password_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        120_000,
    ).hex()
    return hmac.compare_digest(digest, expected_digest)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)

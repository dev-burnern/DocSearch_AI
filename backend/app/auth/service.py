import secrets

from backend.app.auth.models import MEMBER_ROLE, SUPPORTED_ROLES, ApiKeyRecord
from backend.app.core.config import Settings


class AuthService:
    def __init__(self, settings: Settings):
        self._api_keys = self._parse_api_keys(settings.api_keys)

    def validate_api_key(self, api_key: str) -> ApiKeyRecord | None:
        for record in self._api_keys:
            if secrets.compare_digest(record.api_key, api_key):
                return record
        return None

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
                raise ValueError(
                    "DOCSEARCH_API_KEYS role must be one of: admin, member.",
                )

            records.append(
                ApiKeyRecord(
                    api_key=parts[0],
                    workspace_id=parts[1],
                    workspace_name=parts[2],
                    role=role,
                ),
            )

        return records

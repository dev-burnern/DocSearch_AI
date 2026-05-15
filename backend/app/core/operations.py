from typing import Literal

from pydantic import BaseModel

from backend.app.core.config import DEFAULT_API_KEYS, Settings


OperationalStatus = Literal["ready", "not_ready"]


class OperationalCheck(BaseModel):
    name: str
    status: OperationalStatus
    message: str


class ReadinessResponse(BaseModel):
    status: OperationalStatus
    service: str
    checks: list[OperationalCheck]


def build_readiness_response(settings: Settings) -> ReadinessResponse:
    checks = _collect_configuration_checks(settings)
    status: OperationalStatus = (
        "ready"
        if all(check.status == "ready" for check in checks)
        else "not_ready"
    )
    return ReadinessResponse(
        status=status,
        service="docsearch-ai",
        checks=checks,
    )


def _collect_configuration_checks(settings: Settings) -> list[OperationalCheck]:
    if not _is_production(settings):
        return [
            OperationalCheck(
                name="configuration",
                status="ready",
                message="운영 설정 기준을 통과했습니다.",
            )
        ]

    checks: list[OperationalCheck] = []

    if settings.api_keys.strip() == DEFAULT_API_KEYS:
        checks.append(
            OperationalCheck(
                name="api_keys",
                status="not_ready",
                message="운영 환경에서는 개발 기본 API Key를 교체해야 합니다.",
            )
        )

    if settings.debug:
        checks.append(
            OperationalCheck(
                name="debug",
                status="not_ready",
                message="운영 환경에서는 DEBUG를 비활성화해야 합니다.",
            )
        )

    if checks:
        return checks

    return [
        OperationalCheck(
            name="configuration",
            status="ready",
            message="운영 설정 기준을 통과했습니다.",
        )
    ]


def _is_production(settings: Settings) -> bool:
    return settings.app_env.strip().lower() == "production"

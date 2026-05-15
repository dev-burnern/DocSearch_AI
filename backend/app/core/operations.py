from typing import Literal

from pydantic import BaseModel

from backend.app.core.config import DEFAULT_API_KEY, Settings
from backend.app.core.dependency_health import (
    DependencyCheckResult,
    DependencyHealthChecker,
)


OperationalStatus = Literal["ready", "not_ready"]


class OperationalCheck(BaseModel):
    name: str
    status: OperationalStatus
    message: str


class ReadinessResponse(BaseModel):
    status: OperationalStatus
    service: str
    checks: list[OperationalCheck]


def build_readiness_response(
    settings: Settings,
    *,
    dependency_health_checker: DependencyHealthChecker | None = None,
) -> ReadinessResponse:
    checks = _collect_configuration_checks(settings)
    if _should_collect_dependency_checks(settings, checks):
        checker = dependency_health_checker or DependencyHealthChecker()
        checks.extend(_to_operational_checks(checker.check(settings)))

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

    if _uses_development_api_key(settings.api_keys):
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


def _uses_development_api_key(raw_api_keys: str) -> bool:
    for entry in raw_api_keys.split(";"):
        api_key = entry.split("|", maxsplit=1)[0].strip()
        if api_key == DEFAULT_API_KEY:
            return True

    return False


def _should_collect_dependency_checks(
    settings: Settings,
    checks: list[OperationalCheck],
) -> bool:
    if not settings.dependency_health_checks_enabled:
        return False

    return all(check.status == "ready" for check in checks)


def _to_operational_checks(
    dependency_checks: list[DependencyCheckResult],
) -> list[OperationalCheck]:
    return [
        OperationalCheck(
            name=check.name,
            status=check.status,
            message=check.message,
        )
        for check in dependency_checks
    ]

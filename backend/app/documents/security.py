from fastapi import HTTPException, status

from backend.app.auth.models import ADMIN_ROLE, MEMBER_ROLE
from backend.app.documents.models import (
    CONFIDENTIAL_SECURITY_LEVEL,
    GENERAL_SECURITY_LEVEL,
    INTERNAL_SECURITY_LEVEL,
    RESTRICTED_SECURITY_LEVEL,
    SUPPORTED_DOCUMENT_SECURITY_LEVELS,
)

_MEMBER_SECURITY_LEVELS = [GENERAL_SECURITY_LEVEL, INTERNAL_SECURITY_LEVEL]
_ADMIN_SECURITY_LEVELS = [
    GENERAL_SECURITY_LEVEL,
    INTERNAL_SECURITY_LEVEL,
    CONFIDENTIAL_SECURITY_LEVEL,
    RESTRICTED_SECURITY_LEVEL,
]


class DocumentSecurityPermissionError(ValueError):
    pass


def validate_document_security_level(security_level: str) -> str:
    normalized = security_level.strip() or INTERNAL_SECURITY_LEVEL
    if normalized not in SUPPORTED_DOCUMENT_SECURITY_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "DOCUMENT_INVALID_SECURITY_LEVEL",
                "message": (
                    "Document security level must be general, internal, "
                    "confidential, or restricted."
                ),
            },
        )
    return normalized


def validate_document_security_levels(security_levels: list[str] | None) -> list[str] | None:
    if not security_levels:
        return None

    validated: list[str] = []
    for security_level in security_levels:
        normalized = validate_document_security_level(security_level)
        if normalized not in validated:
            validated.append(normalized)
    return validated


def allowed_document_security_levels(role: str) -> list[str]:
    if role == ADMIN_ROLE:
        return _ADMIN_SECURITY_LEVELS.copy()
    return _MEMBER_SECURITY_LEVELS.copy()


def ensure_document_security_level_allowed(role: str, security_level: str) -> None:
    validated_security_level = validate_document_security_level(security_level)
    if validated_security_level not in allowed_document_security_levels(role):
        raise DocumentSecurityPermissionError(
            f"Role {role} cannot access document security level: {validated_security_level}",
        )


def filter_document_security_levels_for_role(
    *,
    role: str,
    requested_security_levels: list[str] | None,
) -> list[str] | None:
    validated_levels = validate_document_security_levels(requested_security_levels)
    if role == ADMIN_ROLE and validated_levels is None:
        return None

    allowed_levels = allowed_document_security_levels(role)
    if validated_levels is None:
        return allowed_levels

    disallowed_levels = [
        security_level
        for security_level in validated_levels
        if security_level not in allowed_levels
    ]
    if disallowed_levels:
        raise DocumentSecurityPermissionError(
            "Requested document security levels are not allowed for this role.",
        )

    return validated_levels

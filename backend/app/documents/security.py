from fastapi import HTTPException, status

from backend.app.documents.models import (
    INTERNAL_SECURITY_LEVEL,
    SUPPORTED_DOCUMENT_SECURITY_LEVELS,
)


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

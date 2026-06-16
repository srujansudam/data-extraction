from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

REDACTION_TEXT = "[REDACTED]"

SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(password|pwd|key|token|secret)\s*=\s*([^;\s,)'\"&]+)"
)
AUTHORIZATION_PATTERN = re.compile(r"(?i)(Authorization\s*:\s*)([^\r\n]+)")
ORACLE_CREDENTIAL_DSN_PATTERN = re.compile(r"(?P<user>[A-Za-z0-9_.-]+)/(?P<pwd>[^@\s]+)@")


def redact_secret_values(message: str, secret_values: Iterable[str] = ()) -> str:
    redacted = message
    for secret_value in sorted(_normalised_secret_values(secret_values), key=len, reverse=True):
        redacted = re.sub(
            re.escape(secret_value),
            REDACTION_TEXT,
            redacted,
            flags=re.IGNORECASE,
        )

    redacted = SENSITIVE_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}={REDACTION_TEXT}",
        redacted,
    )
    redacted = AUTHORIZATION_PATTERN.sub(
        lambda match: f"{match.group(1)}{REDACTION_TEXT}",
        redacted,
    )
    redacted = ORACLE_CREDENTIAL_DSN_PATTERN.sub(
        f"{REDACTION_TEXT}:{REDACTION_TEXT}@",
        redacted,
    )
    return redacted


def sanitize_exception(exc: Exception, secret_values: Iterable[str] = ()) -> str:
    return redact_secret_values(str(exc), secret_values=secret_values)


def secret_values_from_mapping(secret: dict[str, Any]) -> list[str]:
    return [str(value) for value in secret.values() if _has_sensitive_value(value)]


def secret_values_from_mappings(secrets: Iterable[dict[str, Any]]) -> list[str]:
    return [value for secret in secrets for value in secret_values_from_mapping(secret)]


def _normalised_secret_values(secret_values: Iterable[str]) -> set[str]:
    return {str(value) for value in secret_values if _has_sensitive_value(value)}


def _has_sensitive_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""

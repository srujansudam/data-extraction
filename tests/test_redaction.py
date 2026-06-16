from __future__ import annotations

from data_extraction.utils.redaction import redact_secret_values, sanitize_exception


def test_redact_secret_values_replaces_known_values() -> None:
    message = "failed for user secret-user with password secret-password"

    redacted = redact_secret_values(message, ["secret-user", "secret-password"])

    assert "secret-user" not in redacted
    assert "secret-password" not in redacted
    assert redacted.count("[REDACTED]") == 2


def test_redact_secret_values_handles_common_sensitive_patterns() -> None:
    message = (
        "password=abc pwd=def token=ghi key=jkl secret=mno "
        "Authorization: Bearer bearer-token"
    )

    redacted = redact_secret_values(message)

    assert "password=[REDACTED]" in redacted
    assert "pwd=[REDACTED]" in redacted
    assert "token=[REDACTED]" in redacted
    assert "key=[REDACTED]" in redacted
    assert "secret=[REDACTED]" in redacted
    assert "Authorization: [REDACTED]" in redacted
    assert "bearer-token" not in redacted


def test_redact_secret_values_handles_oracle_credential_dsn() -> None:
    message = "connect failed for scott/tiger@//db.example:1521/ORCL"

    redacted = redact_secret_values(message)

    assert "scott/tiger@" not in redacted
    assert "[REDACTED]:[REDACTED]@//db.example:1521/ORCL" in redacted


def test_sanitize_exception_redacts_values() -> None:
    exc = RuntimeError("ORA error password=secret-password")

    assert sanitize_exception(exc) == "ORA error password=[REDACTED]"

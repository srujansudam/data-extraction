from __future__ import annotations

import pytest

from data_extraction.db.key_provider import get_database_key


class FakeSecretProvider:
    def __init__(self, secret: dict[str, str]) -> None:
        self.secret = secret

    def get_secret(self, secret_ref: str) -> dict[str, str]:
        assert secret_ref == "INTERNAL_AUDIT_DB_KEY"
        return self.secret


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("key", "key-value"),
        ("password", "password-value"),
        ("value", "value-field"),
        ("secret", "secret-field"),
    ],
)
def test_get_database_key_returns_supported_fields(field_name: str, field_value: str) -> None:
    provider = FakeSecretProvider({field_name: field_value})

    assert get_database_key(provider, "INTERNAL_AUDIT_DB_KEY") == field_value


def test_get_database_key_prefers_key_over_other_fields() -> None:
    provider = FakeSecretProvider({"key": "preferred", "password": "fallback"})

    assert get_database_key(provider, "INTERNAL_AUDIT_DB_KEY") == "preferred"


def test_get_database_key_raises_for_missing_secret_ref() -> None:
    provider = FakeSecretProvider({"key": "value"})

    with pytest.raises(ValueError, match="database.secret_ref"):
        get_database_key(provider, None)


def test_get_database_key_raises_for_missing_supported_fields() -> None:
    provider = FakeSecretProvider({"username": "user"})

    with pytest.raises(ValueError, match="must return one of"):
        get_database_key(provider, "INTERNAL_AUDIT_DB_KEY")

from __future__ import annotations

from data_extraction.secrets.base import SecretProvider


def get_database_key(secret_provider: SecretProvider, secret_ref: str | None) -> str:
    if not secret_ref:
        raise ValueError("Database encryption requires database.secret_ref.")

    secret = secret_provider.get_secret(secret_ref)

    for key_name in ("key", "password", "value", "secret"):
        value = secret.get(key_name)
        if value and value.strip():
            return value

    raise ValueError(
        f"Database key secret '{secret_ref}' must return one of: key, password, value, secret."
    )

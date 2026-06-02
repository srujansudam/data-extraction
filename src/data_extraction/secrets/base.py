from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from dotenv import load_dotenv


class SecretProvider(Protocol):
    def get_secret(self, secret_ref: str) -> dict[str, str]:
        """Return secret values for a given secret reference."""


@dataclass(frozen=True)
class EnvironmentSecretProvider:
    """
    Local development secret provider.

    This reads secrets from environment variables or a local .env file.
    Production uses the KeePass CLI provider while keeping the same
    get_secret(secret_ref) contract.
    """

    load_dotenv_file: bool = True

    def __post_init__(self) -> None:
        if self.load_dotenv_file:
            load_dotenv()

    def get_secret(self, secret_ref: str) -> dict[str, str]:
        prefix = secret_ref.upper()

        values = {
            key.replace(f"{prefix}_", "").lower(): value
            for key, value in os.environ.items()
            if key.startswith(f"{prefix}_")
        }

        if not values:
            raise KeyError(f"No environment variables found for secret reference: {secret_ref}")

        return values

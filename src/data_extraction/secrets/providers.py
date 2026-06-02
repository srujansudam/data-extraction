from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from data_extraction.secrets.base import EnvironmentSecretProvider, SecretProvider

__all__ = [
    "EnvironmentSecretProvider",
    "KeePassSecretProvider",
    "KeePassCliSecretProvider",
    "SecretProvider",
]


KEEPASS_CUSTOM_FIELDS = ("host", "port", "service_name", "key", "value", "secret")


@dataclass(frozen=True)
class KeePassSecretProvider:
    database_path: str
    key_file_path: str | None = None
    password_env_var: str | None = None

    def get_secret(self, secret_ref: str) -> dict[str, str]:
        database_path = self._validate_database_path()
        key_file_path = self._validate_key_file_path()
        password = self._read_password()

        keepass = self._open_database(database_path, password, key_file_path)
        entry = keepass.find_entries(title=secret_ref, first=True)
        if entry is None:
            raise KeyError(f"KeePass entry not found for secret reference: {secret_ref}")

        secret = self._entry_to_secret(secret_ref, entry)
        if not secret:
            raise ValueError(f"KeePass entry returned an empty secret for {secret_ref}.")

        return secret

    def _validate_database_path(self) -> str:
        if not self.database_path.strip():
            raise ValueError("KeePass database_path is required.")

        path = Path(self.database_path)
        if not path.exists():
            raise FileNotFoundError(f"KeePass database file not found: {path}")

        return str(path)

    def _validate_key_file_path(self) -> str | None:
        if not self.key_file_path or not self.key_file_path.strip():
            return None

        path = Path(self.key_file_path)
        if not path.exists():
            raise FileNotFoundError(f"KeePass key file not found: {path}")

        return str(path)

    def _read_password(self) -> str | None:
        if not self.password_env_var or not self.password_env_var.strip():
            return None

        password = os.getenv(self.password_env_var)
        if not password:
            raise ValueError(f"KeePass password environment variable is not set: {self.password_env_var}")

        return password

    @staticmethod
    def _open_database(
        database_path: str,
        password: str | None,
        key_file_path: str | None,
    ) -> Any:
        try:
            from pykeepass import PyKeePass
        except ImportError as exc:
            raise RuntimeError(
                "PyKeePass is required for secrets.provider=keepass. "
                "Install the pykeepass package or use keepass_cli fallback."
            ) from exc

        return PyKeePass(database_path, password=password, keyfile=key_file_path)

    @staticmethod
    def _entry_to_secret(secret_ref: str, entry: Any) -> dict[str, str]:
        secret: dict[str, str] = {}

        username = getattr(entry, "username", None)
        password = getattr(entry, "password", None)
        custom_properties = getattr(entry, "custom_properties", None) or {}

        if (
            secret_ref == "INTERNAL_AUDIT_DB_KEY"
            and custom_properties.get("key") is None
            and password is not None
        ):
            return {"key": str(password)}

        if username is not None:
            secret["username"] = str(username)
        if password is not None:
            secret["password"] = str(password)

        for field in KEEPASS_CUSTOM_FIELDS:
            value = custom_properties.get(field)
            if value is not None:
                secret[field] = str(value)

        return secret


@dataclass(frozen=True)
class KeePassCliSecretProvider:
    executable_path: str
    command_template: str

    def get_secret(self, secret_ref: str) -> dict[str, str]:
        if not self.executable_path.strip():
            raise ValueError("KeePass CLI executable_path is required.")

        if not self.command_template.strip():
            raise ValueError("KeePass CLI command_template is required.")

        if "{secret_ref}" not in self.command_template:
            raise ValueError("KeePass CLI command_template must include {secret_ref}.")

        command_args = shlex.split(
            self.command_template.format(secret_ref=secret_ref),
        )
        try:
            completed_process = subprocess.run(
                [self.executable_path, *command_args],
                capture_output=True,
                check=False,
                text=True,
            )
        except OSError as exc:
            raise RuntimeError(f"Could not execute KeePass CLI wrapper: {exc}") from exc

        if completed_process.returncode != 0:
            raise RuntimeError(
                "KeePass CLI wrapper failed "
                f"(exit code {completed_process.returncode}; "
                f"stdout bytes={len(completed_process.stdout or '')}; "
                f"stderr bytes={len(completed_process.stderr or '')})."
            )

        try:
            raw_secret = json.loads(completed_process.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError("KeePass CLI wrapper returned invalid JSON.") from exc

        if not isinstance(raw_secret, dict) or not raw_secret:
            raise ValueError(f"KeePass CLI wrapper returned an empty secret for {secret_ref}.")

        secret = {str(key): str(value) for key, value in raw_secret.items() if value is not None}
        if not secret:
            raise ValueError(f"KeePass CLI wrapper returned an empty secret for {secret_ref}.")

        return secret

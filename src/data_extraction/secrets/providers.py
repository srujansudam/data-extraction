from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from data_extraction.secrets.password_safe import EnvironmentSecretProvider, SecretProvider

__all__ = [
    "EnvironmentSecretProvider",
    "PasswordSafeCliSecretProvider",
    "PasswordSafeHttpSecretProvider",
    "SecretProvider",
]


@dataclass(frozen=True)
class PasswordSafeCliSecretProvider:
    executable_path: str
    command_template: str

    def get_secret(self, secret_ref: str) -> dict[str, str]:
        executable = Path(self.executable_path)
        if not self.executable_path.strip() or not executable.exists():
            raise FileNotFoundError(
                f"Password Safe CLI executable not found: {self.executable_path}"
            )

        if "{secret_ref}" not in self.command_template:
            raise ValueError("Password Safe CLI command_template must include {secret_ref}.")

        command_args = shlex.split(
            self.command_template.format(secret_ref=secret_ref),
            posix=False,
        )
        try:
            completed_process = subprocess.run(
                [str(executable), *command_args],
                capture_output=True,
                check=False,
                text=True,
            )
        except OSError as exc:
            raise RuntimeError(f"Could not execute Password Safe CLI: {exc}") from exc

        if completed_process.returncode != 0:
            stderr = completed_process.stderr.strip()
            message = stderr or f"exit code {completed_process.returncode}"
            raise RuntimeError(f"Password Safe CLI command failed: {message}")

        try:
            raw_secret = json.loads(completed_process.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError("Password Safe CLI returned invalid JSON.") from exc

        if not isinstance(raw_secret, dict) or not raw_secret:
            raise ValueError(f"Password Safe CLI returned an empty secret for {secret_ref}.")

        return {str(key): str(value) for key, value in raw_secret.items()}


@dataclass(frozen=True)
class PasswordSafeHttpSecretProvider:
    base_url: str
    auth_secret_ref: str
    verify_ssl: bool = True
    timeout_seconds: int = 30

    def get_secret(self, secret_ref: str) -> dict[str, str]:
        raise NotImplementedError(
            "Password Safe HTTP provider requires client API details before implementation."
        )

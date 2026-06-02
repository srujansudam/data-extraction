from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass

from data_extraction.secrets.base import EnvironmentSecretProvider, SecretProvider

__all__ = [
    "EnvironmentSecretProvider",
    "KeePassCliSecretProvider",
    "SecretProvider",
]


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

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from data_extraction.secrets.providers import (
    PasswordSafeCliSecretProvider,
    PasswordSafeHttpSecretProvider,
)


def test_password_safe_cli_provider_returns_json_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "password-safe.exe"
    executable.write_text("", encoding="utf-8")
    calls = []

    def fake_run(args, capture_output, check, text):
        calls.append(args)
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps({"username": "user", "password": "secret", "port": 1521}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = PasswordSafeCliSecretProvider(
        executable_path=str(executable),
        command_template="get --secret {secret_ref}",
    )

    secret = provider.get_secret("ORION_DB")

    assert calls == [[str(executable), "get", "--secret", "ORION_DB"]]
    assert secret == {"username": "user", "password": "secret", "port": "1521"}


def test_password_safe_cli_provider_raises_for_missing_executable(tmp_path: Path) -> None:
    provider = PasswordSafeCliSecretProvider(
        executable_path=str(tmp_path / "missing.exe"),
        command_template="get --secret {secret_ref}",
    )

    with pytest.raises(FileNotFoundError, match="Password Safe CLI executable not found"):
        provider.get_secret("ORION_DB")


def test_password_safe_cli_provider_raises_for_command_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "password-safe.exe"
    executable.write_text("", encoding="utf-8")

    def fake_run(args, capture_output, check, text):
        return subprocess.CompletedProcess(args=args, returncode=2, stdout="", stderr="denied")

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = PasswordSafeCliSecretProvider(
        executable_path=str(executable),
        command_template="get --secret {secret_ref}",
    )

    with pytest.raises(RuntimeError, match="Password Safe CLI command failed: denied"):
        provider.get_secret("ORION_DB")


def test_password_safe_cli_provider_raises_for_invalid_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "password-safe.exe"
    executable.write_text("", encoding="utf-8")

    def fake_run(args, capture_output, check, text):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="not json", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = PasswordSafeCliSecretProvider(
        executable_path=str(executable),
        command_template="get --secret {secret_ref}",
    )

    with pytest.raises(ValueError, match="invalid JSON"):
        provider.get_secret("ORION_DB")


def test_password_safe_cli_provider_raises_for_empty_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "password-safe.exe"
    executable.write_text("", encoding="utf-8")

    def fake_run(args, capture_output, check, text):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = PasswordSafeCliSecretProvider(
        executable_path=str(executable),
        command_template="get --secret {secret_ref}",
    )

    with pytest.raises(ValueError, match="empty secret"):
        provider.get_secret("ORION_DB")


def test_password_safe_http_provider_is_explicitly_not_implemented() -> None:
    provider = PasswordSafeHttpSecretProvider(base_url="https://password-safe.example", auth_secret_ref="AUTH")

    with pytest.raises(NotImplementedError, match="requires client API details"):
        provider.get_secret("ORION_DB")

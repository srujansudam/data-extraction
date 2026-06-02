from __future__ import annotations

import json
import subprocess

import pytest

from data_extraction.secrets.providers import KeePassCliSecretProvider


def test_keepass_cli_provider_returns_json_secret(monkeypatch: pytest.MonkeyPatch) -> None:
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
    provider = KeePassCliSecretProvider(
        executable_path="powershell.exe",
        command_template="-File wrapper.ps1 -SecretRef {secret_ref}",
    )

    secret = provider.get_secret("ORION_DB")

    assert calls == [["powershell.exe", "-File", "wrapper.ps1", "-SecretRef", "ORION_DB"]]
    assert secret == {"username": "user", "password": "secret", "port": "1521"}


def test_keepass_cli_provider_requires_executable_path() -> None:
    provider = KeePassCliSecretProvider(
        executable_path="",
        command_template="-File wrapper.ps1 -SecretRef {secret_ref}",
    )

    with pytest.raises(ValueError, match="executable_path is required"):
        provider.get_secret("ORION_DB")


def test_keepass_cli_provider_requires_command_template() -> None:
    provider = KeePassCliSecretProvider(
        executable_path="powershell.exe",
        command_template="",
    )

    with pytest.raises(ValueError, match="command_template is required"):
        provider.get_secret("ORION_DB")


def test_keepass_cli_provider_requires_secret_ref_placeholder() -> None:
    provider = KeePassCliSecretProvider(
        executable_path="powershell.exe",
        command_template="-File wrapper.ps1",
    )

    with pytest.raises(ValueError, match="must include {secret_ref}"):
        provider.get_secret("ORION_DB")


def test_keepass_cli_provider_raises_for_process_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(args, capture_output, check, text):
        raise OSError("not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = KeePassCliSecretProvider(
        executable_path="missing.exe",
        command_template="-File wrapper.ps1 -SecretRef {secret_ref}",
    )

    with pytest.raises(RuntimeError, match="Could not execute KeePass CLI wrapper"):
        provider.get_secret("ORION_DB")


def test_keepass_cli_provider_raises_for_command_failure_without_leaking_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(args, capture_output, check, text):
        return subprocess.CompletedProcess(
            args=args,
            returncode=2,
            stdout='{"password":"secret-value"}',
            stderr="denied secret-value",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = KeePassCliSecretProvider(
        executable_path="powershell.exe",
        command_template="-File wrapper.ps1 -SecretRef {secret_ref}",
    )

    with pytest.raises(RuntimeError) as exc_info:
        provider.get_secret("ORION_DB")

    message = str(exc_info.value)
    assert "KeePass CLI wrapper failed" in message
    assert "secret-value" not in message
    assert "stdout bytes=" in message
    assert "stderr bytes=" in message


def test_keepass_cli_provider_raises_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(args, capture_output, check, text):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="not json", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = KeePassCliSecretProvider(
        executable_path="powershell.exe",
        command_template="-File wrapper.ps1 -SecretRef {secret_ref}",
    )

    with pytest.raises(ValueError, match="invalid JSON"):
        provider.get_secret("ORION_DB")


def test_keepass_cli_provider_raises_for_empty_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(args, capture_output, check, text):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    provider = KeePassCliSecretProvider(
        executable_path="powershell.exe",
        command_template="-File wrapper.ps1 -SecretRef {secret_ref}",
    )

    with pytest.raises(ValueError, match="empty secret"):
        provider.get_secret("ORION_DB")

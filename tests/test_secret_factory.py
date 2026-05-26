from __future__ import annotations

from pathlib import Path

import pytest

from data_extraction.config.settings import load_settings
from data_extraction.secrets.factory import create_secret_provider
from data_extraction.secrets.providers import (
    EnvironmentSecretProvider,
    PasswordSafeCliSecretProvider,
    PasswordSafeHttpSecretProvider,
)


def write_config(tmp_path: Path, provider: str) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
app:
  name: data-extraction
database:
  path: {(tmp_path / "test.db").as_posix()}
sources:
  orion:
    secret_ref: ORION_DB
  flexcube:
    secret_ref: FLEXCUBE_DB
  hris:
    secret_ref: HRIS_DB
  lotus_notes:
    enabled: false
extraction:
  timezone: Europe/Malta
logging:
  level: INFO
  folder: logs
secrets:
  provider: {provider}
  password_safe_cli:
    executable_path: C:/PasswordSafe/ps.exe
    command_template: get --secret {{secret_ref}}
  password_safe_http:
    base_url: https://password-safe.example
    auth_secret_ref: PASSWORD_SAFE_AUTH
    verify_ssl: true
    timeout_seconds: 30
""",
        encoding="utf-8",
    )
    return config_path


@pytest.mark.parametrize(
    ("provider_name", "expected_type"),
    [
        ("environment", EnvironmentSecretProvider),
        ("password_safe_cli", PasswordSafeCliSecretProvider),
        ("password_safe_http", PasswordSafeHttpSecretProvider),
    ],
)
def test_create_secret_provider_returns_configured_provider(
    tmp_path: Path,
    provider_name: str,
    expected_type: type,
) -> None:
    settings = load_settings(write_config(tmp_path, provider_name))

    provider = create_secret_provider(settings)

    assert isinstance(provider, expected_type)


def test_create_secret_provider_raises_for_unknown_provider(tmp_path: Path) -> None:
    settings = load_settings(write_config(tmp_path, "unknown"))

    with pytest.raises(ValueError, match="Unknown secret provider"):
        create_secret_provider(settings)

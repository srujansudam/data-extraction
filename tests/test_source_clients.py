from __future__ import annotations

from pathlib import Path

import pytest

from data_extraction.config.settings import load_settings
from data_extraction.pipeline.source_clients import build_oracle_source_clients, close_source_clients


class FakeSecretProvider:
    def __init__(self) -> None:
        self.secret_refs: list[str] = []

    def get_secret(self, secret_ref: str) -> dict[str, str]:
        self.secret_refs.append(secret_ref)
        return {
            "username": f"{secret_ref}_user",
            "password": "password",
            "host": "localhost",
            "port": "1521",
            "service_name": "ORCL",
        }


class FakeOracleConnector:
    created_refs: list[str] = []
    connected_refs: list[str] = []
    closed_refs: list[str] = []

    def __init__(self, secret_ref: str) -> None:
        self.secret_ref = secret_ref

    @classmethod
    def from_secret_ref(cls, secret_provider: FakeSecretProvider, secret_ref: str) -> FakeOracleConnector:
        secret_provider.get_secret(secret_ref)
        cls.created_refs.append(secret_ref)
        return cls(secret_ref)

    def connect(self) -> None:
        self.connected_refs.append(self.secret_ref)

    def close(self) -> None:
        self.closed_refs.append(self.secret_ref)


def write_config(tmp_path: Path, hris_secret_ref: str | None = "HRIS_DB") -> Path:
    hris_secret_line = f"    secret_ref: {hris_secret_ref}\n" if hris_secret_ref is not None else ""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
app:
  name: data-extraction
  environment: test
database:
  type: sqlite
  path: {(tmp_path / "test.db").as_posix()}
  encryption: none
sources:
  orion:
    type: oracle
    secret_ref: ORION_DB
    enabled: true
  flexcube:
    type: oracle
    secret_ref: FLEXCUBE_DB
    enabled: true
  hris:
    type: oracle
{hris_secret_line}    enabled: true
  lotus_notes:
    enabled: true
    mode: excel
extraction:
  daily_mode: previous_day
  backfill_years: 2
  timezone: Europe/Malta
logging:
  level: INFO
  folder: logs
""",
        encoding="utf-8",
    )
    return config_path


def test_build_oracle_source_clients_uses_secret_refs_and_connects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeOracleConnector.created_refs = []
    FakeOracleConnector.connected_refs = []
    FakeOracleConnector.closed_refs = []
    monkeypatch.setattr(
        "data_extraction.pipeline.source_clients.OracleConnector",
        FakeOracleConnector,
    )
    settings = load_settings(write_config(tmp_path))
    secret_provider = FakeSecretProvider()

    source_clients = build_oracle_source_clients(settings, secret_provider)

    assert list(source_clients) == ["orion", "flexcube", "hris"]
    assert secret_provider.secret_refs == ["ORION_DB", "FLEXCUBE_DB", "HRIS_DB"]
    assert FakeOracleConnector.created_refs == ["ORION_DB", "FLEXCUBE_DB", "HRIS_DB"]
    assert FakeOracleConnector.connected_refs == ["ORION_DB", "FLEXCUBE_DB", "HRIS_DB"]

    close_source_clients(source_clients)
    assert FakeOracleConnector.closed_refs == ["ORION_DB", "FLEXCUBE_DB", "HRIS_DB"]


def test_build_oracle_source_clients_raises_for_missing_secret_ref(tmp_path: Path) -> None:
    settings = load_settings(write_config(tmp_path, hris_secret_ref=None))

    with pytest.raises(ValueError, match="Required source 'hris' is missing secret_ref"):
        build_oracle_source_clients(settings, FakeSecretProvider())

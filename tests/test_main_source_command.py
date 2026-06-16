from __future__ import annotations

from pathlib import Path

import pytest

from data_extraction.main import run_source_test
from data_extraction.pipeline.source_health import HEALTH_CHECK_SQL


class FakeSecretProvider:
    def get_secret(self, secret_ref: str) -> dict[str, str]:
        return {
            "username": f"{secret_ref}_user",
            "password": "super-secret-password",
            "host": "secret-db.example",
            "port": "1521",
            "service_name": "SECRET_SERVICE",
        }


class FakeOracleConnector:
    created_refs: list[str] = []
    connected_refs: list[str] = []
    queried_sql: list[str] = []
    closed_refs: list[str] = []
    failing_ref: str | None = None

    def __init__(self, secret_ref: str) -> None:
        self.secret_ref = secret_ref

    @classmethod
    def reset(cls) -> None:
        cls.created_refs = []
        cls.connected_refs = []
        cls.queried_sql = []
        cls.closed_refs = []
        cls.failing_ref = None

    @classmethod
    def from_secret_ref(
        cls,
        secret_provider: FakeSecretProvider,
        secret_ref: str,
    ) -> FakeOracleConnector:
        secret_provider.get_secret(secret_ref)
        cls.created_refs.append(secret_ref)
        return cls(secret_ref)

    def connect(self) -> None:
        self.connected_refs.append(self.secret_ref)
        if self.secret_ref == self.failing_ref:
            raise RuntimeError(
                "ORA-01017: invalid username/password; logon denied "
                "for ORION_DB_user at secret-db.example:1521/SECRET_SERVICE "
                "using super-secret-password"
            )

    def query_all(self, sql: str) -> list[dict[str, int]]:
        self.queried_sql.append(sql)
        return [{"health_check": 1}]

    def close(self) -> None:
        self.closed_refs.append(self.secret_ref)


def write_config(tmp_path: Path) -> Path:
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
  folder: {(tmp_path / "logs").as_posix()}
secrets:
  provider: environment
""",
        encoding="utf-8",
    )
    return config_path


def prepare_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeOracleConnector.reset()
    monkeypatch.setattr(
        "data_extraction.main.create_secret_provider",
        lambda settings: FakeSecretProvider(),
    )
    monkeypatch.setattr(
        "data_extraction.pipeline.source_health.OracleConnector",
        FakeOracleConnector,
    )


def test_source_orion_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    prepare_fakes(monkeypatch)

    successful = run_source_test(str(write_config(tmp_path)), "orion")

    assert successful == ["orion"]
    assert FakeOracleConnector.created_refs == ["ORION_DB"]
    assert FakeOracleConnector.connected_refs == ["ORION_DB"]
    assert FakeOracleConnector.queried_sql == [HEALTH_CHECK_SQL]
    assert FakeOracleConnector.closed_refs == ["ORION_DB"]
    assert "Source connectivity succeeded: orion" in capsys.readouterr().err


def test_source_all_tests_all_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepare_fakes(monkeypatch)

    successful = run_source_test(str(write_config(tmp_path)), "all")

    assert successful == ["orion", "flexcube", "hris"]
    assert FakeOracleConnector.created_refs == ["ORION_DB", "FLEXCUBE_DB", "HRIS_DB"]
    assert FakeOracleConnector.queried_sql == [HEALTH_CHECK_SQL] * 3
    assert FakeOracleConnector.closed_refs == ["ORION_DB", "FLEXCUBE_DB", "HRIS_DB"]


def test_source_unknown_raises_clear_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepare_fakes(monkeypatch)

    with pytest.raises(ValueError, match="Unknown source 'unknown'"):
        run_source_test(str(write_config(tmp_path)), "unknown")


def test_source_failure_does_not_leak_secret_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    prepare_fakes(monkeypatch)
    FakeOracleConnector.failing_ref = "ORION_DB"

    with pytest.raises(RuntimeError, match="Source connectivity test failed for: orion"):
        run_source_test(str(write_config(tmp_path)), "orion")

    log_text = capsys.readouterr().err
    assert (
        "Source connectivity failed: orion - RuntimeError: "
        "ORA-01017: invalid username/password; logon denied"
    ) in log_text
    assert "ORION_DB_user" not in log_text
    assert "secret-db.example" not in log_text
    assert "super-secret-password" not in log_text
    assert "SECRET_SERVICE" not in log_text
    assert ":1521/" not in log_text
    assert "[REDACTED]" in log_text
    assert FakeOracleConnector.closed_refs == ["ORION_DB"]

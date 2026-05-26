from __future__ import annotations

from pathlib import Path

from data_extraction.main import run_secret_test


class FakeSecretProvider:
    def get_secret(self, secret_ref: str) -> dict[str, str]:
        assert secret_ref == "ORION_DB"
        return {
            "username": "orion_user",
            "password": "super-secret-password",
            "host": "db.example",
            "port": "1521",
            "service_name": "ORCL",
        }


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
  folder: logs
secrets:
  provider: environment
""",
        encoding="utf-8",
    )
    return config_path


def test_test_secret_logs_keys_but_not_values(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "data_extraction.main.create_secret_provider",
        lambda settings: FakeSecretProvider(),
    )
    run_secret_test(str(write_config(tmp_path)), "ORION_DB")

    log_text = capsys.readouterr().err
    assert "username" in log_text
    assert "password" in log_text
    assert "host" in log_text
    assert "port" in log_text
    assert "service_name" in log_text
    assert "orion_user" not in log_text
    assert "super-secret-password" not in log_text
    assert "db.example" not in log_text
    assert "ORCL" not in log_text

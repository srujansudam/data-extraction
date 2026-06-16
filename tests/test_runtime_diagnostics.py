from __future__ import annotations

from pathlib import Path

from data_extraction.main import build_parser, diagnose_runtime


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
    enabled: true
  flexcube:
    secret_ref: FLEXCUBE_DB
    enabled: true
  hris:
    secret_ref: HRIS_DB
    enabled: true
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


def test_cli_parser_supports_diagnose_runtime() -> None:
    parser = build_parser()

    args = parser.parse_args(["diagnose-runtime"])

    assert args.command == "diagnose-runtime"


def test_diagnose_runtime_imports_oracle_thin_dependencies(tmp_path: Path) -> None:
    diagnostics = diagnose_runtime(str(write_config(tmp_path)))

    assert diagnostics["cryptography"] != ""
    assert diagnostics["cffi"] != ""
    assert diagnostics["oracledb"] != ""

from __future__ import annotations

from pathlib import Path

from data_extraction.preflight import run_preflight


def write_config(
    tmp_path: Path,
    *,
    include_orion_secret_ref: bool = True,
    include_lotus_files: bool = True,
    secrets_block: str = "provider: environment",
) -> Path:
    db_path = tmp_path / "nested" / "data" / "audit.db"
    log_folder = tmp_path / "nested" / "logs"
    orion_secret_line = "    secret_ref: ORION_DB\n" if include_orion_secret_ref else ""
    lotus_files = (
        """
    files:
      lotus_bov_employees: data/lotus_notes/incoming/bov_employees.xlsx
      lotus_legal_rulings: data/lotus_notes/incoming/legal_rulings.xlsx
      lotus_garnishee_orders: data/lotus_notes/incoming/garnishee_orders.xlsx
      lotus_poa_revocation: data/lotus_notes/incoming/poa_revocation.xlsx
      lotus_discrepancies_management: data/lotus_notes/incoming/discrepancies_management.xlsx
"""
        if include_lotus_files
        else ""
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
app:
  name: data-extraction
  environment: test

database:
  type: sqlite
  path: {db_path.as_posix()}
  encryption: none
  secret_ref: INTERNAL_AUDIT_DB_KEY

sources:
  orion:
    type: oracle
{orion_secret_line}    enabled: true
  flexcube:
    type: oracle
    secret_ref: FLEXCUBE_DB
    enabled: true
  hris:
    type: oracle
    secret_ref: HRIS_DB
    enabled: true
  lotus_notes:
    enabled: true
    mode: excel
    secret_ref: LOTUS_NOTES
    excel_input_folder: data/lotus_notes/incoming
{lotus_files}    corba_java_command: java
    corba_jar_path: java/lotus-corba-reader/dist/lotus-corba-reader.jar

extraction:
  daily_mode: previous_day
  backfill_years: 2
  timezone: Europe/Malta

logging:
  level: INFO
  folder: {log_folder.as_posix()}

secrets:
  {secrets_block}
""",
        encoding="utf-8",
    )
    return config_path


def check_by_name(result: dict[str, object], name: str) -> dict[str, str]:
    checks = result["checks"]
    assert isinstance(checks, list)
    for check in checks:
        assert isinstance(check, dict)
        if check.get("name") == name:
            return check
    raise AssertionError(f"Missing preflight check: {name}")


def test_preflight_passes_with_config_example() -> None:
    result = run_preflight("config/config.example.yaml")

    assert result["status"] == "passed"


def test_preflight_fails_if_required_source_secret_ref_is_missing(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, include_orion_secret_ref=False)

    result = run_preflight(str(config_path))

    assert result["status"] == "failed"
    orion_check = check_by_name(result, "orion_secret_ref")
    assert orion_check["status"] == "failed"
    assert "missing secret_ref" in orion_check["message"]


def test_preflight_fails_if_lotus_file_mapping_is_missing_required_keys(tmp_path: Path) -> None:
    config_path = write_config(tmp_path, include_lotus_files=False)

    result = run_preflight(str(config_path))

    assert result["status"] == "failed"
    lotus_check = check_by_name(result, "lotus_excel_files")
    assert lotus_check["status"] == "failed"
    assert "missing keys" in lotus_check["message"]


def test_preflight_creates_db_and_log_folders_under_tmp_path_config(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)

    result = run_preflight(str(config_path))

    assert result["status"] == "passed"
    assert (tmp_path / "nested" / "data").is_dir()
    assert (tmp_path / "nested" / "logs").is_dir()
    assert (tmp_path / "nested" / "data" / "audit.db").exists()


def test_preflight_passes_environment_secret_provider_with_local_dev_message(
    tmp_path: Path,
) -> None:
    result = run_preflight(str(write_config(tmp_path)))

    provider_check = check_by_name(result, "secret_provider")
    assert provider_check["status"] == "passed"
    assert "local development" in provider_check["message"]


def test_preflight_fails_when_password_safe_cli_config_is_incomplete(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        secrets_block="""
provider: password_safe_cli
  password_safe_cli:
    executable_path: ""
    command_template: ""
""".strip(),
    )

    result = run_preflight(str(config_path))

    provider_check = check_by_name(result, "secret_provider")
    assert provider_check["status"] == "failed"
    assert "executable_path" in provider_check["message"]
    assert "command_template" in provider_check["message"]

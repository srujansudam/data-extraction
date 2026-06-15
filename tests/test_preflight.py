from __future__ import annotations

from pathlib import Path
from textwrap import indent

from data_extraction.preflight import run_preflight


def write_config(
    tmp_path: Path,
    *,
    include_orion_secret_ref: bool = True,
    include_lotus_files: bool = True,
    secrets_block: str = "provider: environment",
    database_encryption: str = "none",
    database_secret_ref: str | None = "INTERNAL_AUDIT_DB_KEY",
) -> Path:
    db_path = tmp_path / "nested" / "data" / "audit.db"
    log_folder = tmp_path / "nested" / "logs"
    orion_secret_line = "    secret_ref: ORION_DB\n" if include_orion_secret_ref else ""
    database_secret_ref_line = (
        f"  secret_ref: {database_secret_ref}\n" if database_secret_ref is not None else ""
    )
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
    secrets_yaml = indent(secrets_block.strip(), "  ")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
app:
  name: data-extraction
  environment: test

database:
  type: sqlite
  path: {db_path.as_posix()}
  encryption: {database_encryption}
{database_secret_ref_line}  see_activation_key: ""

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
{secrets_yaml}
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


def test_preflight_fails_if_see_database_secret_ref_is_missing(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        database_encryption="see",
        database_secret_ref=None,
    )

    result = run_preflight(str(config_path))

    assert result["status"] == "failed"
    encryption_check = check_by_name(result, "database_encryption")
    assert encryption_check["status"] == "failed"
    assert "database.secret_ref" in encryption_check["message"]


def test_preflight_fails_if_see_database_key_cannot_be_retrieved(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = write_config(
        tmp_path,
        database_encryption="see",
        database_secret_ref="INTERNAL_AUDIT_DB_KEY",
    )
    monkeypatch.delenv("INTERNAL_AUDIT_DB_KEY_KEY", raising=False)
    monkeypatch.delenv("INTERNAL_AUDIT_DB_KEY_PASSWORD", raising=False)
    monkeypatch.delenv("INTERNAL_AUDIT_DB_KEY_VALUE", raising=False)
    monkeypatch.delenv("INTERNAL_AUDIT_DB_KEY_SECRET", raising=False)

    result = run_preflight(str(config_path))

    assert result["status"] == "failed"
    key_check = check_by_name(result, "database_key")
    assert key_check["status"] == "failed"
    assert "Could not retrieve SQLite SEE key" in key_check["message"]


def test_preflight_fails_clearly_when_see_library_is_not_active(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = write_config(
        tmp_path,
        database_encryption="see",
        database_secret_ref="INTERNAL_AUDIT_DB_KEY",
    )
    monkeypatch.setenv("INTERNAL_AUDIT_DB_KEY_KEY", "test-key")

    result = run_preflight(str(config_path))

    assert result["status"] == "failed"
    schema_check = check_by_name(result, "database_schema")
    assert schema_check["status"] == "failed"
    assert "SQLite SEE key was not accepted" in schema_check["message"]


def test_preflight_passes_environment_secret_provider_with_local_dev_message(
    tmp_path: Path,
) -> None:
    result = run_preflight(str(write_config(tmp_path)))

    provider_check = check_by_name(result, "secret_provider")
    assert provider_check["status"] == "passed"
    assert "local development" in provider_check["message"]


def test_preflight_fails_when_keepass_cli_config_is_incomplete(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        secrets_block="""
provider: keepass_cli
keepass_cli:
  executable_path: ""
  command_template: ""
""".strip(),
    )

    result = run_preflight(str(config_path))

    provider_check = check_by_name(result, "secret_provider")
    assert provider_check["status"] == "failed"
    assert "executable_path" in provider_check["message"]
    assert "command_template" in provider_check["message"]


def test_preflight_fails_when_keepass_cli_template_lacks_secret_ref(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        secrets_block="""
provider: keepass_cli
keepass_cli:
  executable_path: powershell.exe
  command_template: -File scripts/get_keepass_secret.ps1
""".strip(),
    )

    result = run_preflight(str(config_path))

    provider_check = check_by_name(result, "secret_provider")
    assert provider_check["status"] == "failed"
    assert "{secret_ref}" in provider_check["message"]


def test_preflight_fails_when_keepass_config_is_incomplete(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        secrets_block="""
provider: keepass
keepass:
  database_path: ""
  key_file_path: ""
  password_env_var: ""
""".strip(),
    )

    result = run_preflight(str(config_path))

    provider_check = check_by_name(result, "secret_provider")
    assert provider_check["status"] == "failed"
    assert "database_path" in provider_check["message"]
    assert "key_file_path or password_env_var" in provider_check["message"]


def test_preflight_fails_when_keepass_database_file_is_missing(tmp_path: Path) -> None:
    key_file_path = tmp_path / "secrets.keyx"
    key_file_path.write_text("not-real-key-file", encoding="utf-8")
    config_path = write_config(
        tmp_path,
        secrets_block=f"""
provider: keepass
keepass:
  database_path: {(tmp_path / "missing.kdbx").as_posix()}
  key_file_path: {key_file_path.as_posix()}
  password_env_var: ""
""".strip(),
    )

    result = run_preflight(str(config_path))

    provider_check = check_by_name(result, "secret_provider")
    assert provider_check["status"] == "failed"
    assert "KeePass database file not found" in provider_check["message"]


def test_preflight_fails_when_keepass_key_file_is_missing(tmp_path: Path) -> None:
    database_path = tmp_path / "secrets.kdbx"
    database_path.write_bytes(b"not-real-kdbx")
    config_path = write_config(
        tmp_path,
        secrets_block=f"""
provider: keepass
keepass:
  database_path: {database_path.as_posix()}
  key_file_path: {(tmp_path / "missing.keyx").as_posix()}
  password_env_var: ""
""".strip(),
    )

    result = run_preflight(str(config_path))

    provider_check = check_by_name(result, "secret_provider")
    assert provider_check["status"] == "failed"
    assert "KeePass key file not found" in provider_check["message"]


def test_preflight_passes_keepass_file_checks_when_files_exist(tmp_path: Path) -> None:
    database_path = tmp_path / "secrets.kdbx"
    key_file_path = tmp_path / "secrets.keyx"
    database_path.write_bytes(b"not-real-kdbx")
    key_file_path.write_text("not-real-key-file", encoding="utf-8")
    config_path = write_config(
        tmp_path,
        secrets_block=f"""
provider: keepass
keepass:
  database_path: {database_path.as_posix()}
  key_file_path: {key_file_path.as_posix()}
  password_env_var: ""
""".strip(),
    )

    result = run_preflight(str(config_path))

    provider_check = check_by_name(result, "secret_provider")
    assert provider_check["status"] == "passed"
    assert provider_check["message"] == "KeePass provider config is valid."
    database_path_check = check_by_name(result, "keepass_database_path")
    assert database_path_check["status"] == "passed"
    assert "database file is available" in database_path_check["message"]
    key_file_check = check_by_name(result, "keepass_key_file_path")
    assert key_file_check["status"] == "passed"
    assert "key file is available" in key_file_check["message"]
    assert result["status"] == "passed"


def test_preflight_skips_keepass_file_checks_for_template_config(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        secrets_block="""
provider: keepass
keepass:
  database_path: secrets/internal_audit_secrets.kdbx
  key_file_path: secrets/internal_audit_secrets.keyx
  password_env_var: ""
""".strip(),
    )
    template_path = tmp_path / "config.production.template.yaml"
    config_path.replace(template_path)

    result = run_preflight(str(template_path))

    provider_check = check_by_name(result, "secret_provider")
    assert provider_check["status"] == "passed"
    assert "template config" in provider_check["message"]

from __future__ import annotations

from pathlib import Path

from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.dev.dry_run import run_dry_pipeline


def write_config(tmp_path: Path) -> Path:
    db_path = tmp_path / "dry_run.db"
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
    secret_ref: ORION_DB
    enabled: true
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
    corba_java_command: java
    corba_jar_path: java/lotus-corba-reader/dist/lotus-corba-reader.jar

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


def test_dry_run_pipeline_completes_without_real_source_connections(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    run_id = run_dry_pipeline(config_path=str(config_path), reset_db=True)

    assert run_id > 0

    db = SQLiteAdapter(str(tmp_path / "dry_run.db"))
    db.connect()
    try:
        run_row = db.query_one(
            "SELECT status, run_type, triggered_by, notes FROM extraction_run WHERE run_id = ?",
            [run_id],
        )
        assert run_row == {
            "status": "completed",
            "run_type": "dry_run",
            "triggered_by": "manual",
            "notes": "Local dry-run pipeline",
        }

        for table_name in [
            "account_data",
            "customer_data",
            "transaction_data",
            "legal_rulings",
            "staff",
            "users",
            "related_parties",
            "third_party_access",
            "allowed_third_party",
        ]:
            row = db.query_one(f"SELECT COUNT(*) AS row_count FROM {table_name}")
            assert row is not None
            assert row["row_count"] >= 1
    finally:
        db.close()

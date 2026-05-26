from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from data_extraction.db.schema import create_staging_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.staging.writer import StagingWriter


def test_staging_writer_inserts_json_payload_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_staging_tables(db)
        writer = StagingWriter(db)

        rows_inserted = writer.write_rows(
            staging_table="stg_flexcube_office_accounts",
            run_id=42,
            source_system="flexcube",
            source_object="FCBOV.STTM_CUST_ACCOUNT",
            rows=[
                {"office_account_number": "OFF001", "customer_code": "C001"},
                {"office_account_number": "OFF002", "customer_code": "C002"},
            ],
        )

        rows = db.query_all(
            """
            SELECT run_id, source_system, source_object, source_row_hash, source_payload
            FROM stg_flexcube_office_accounts
            ORDER BY staging_id
            """
        )
        expected_payload = json.dumps(
            {"office_account_number": "OFF001", "customer_code": "C001"},
            default=str,
            sort_keys=True,
        )

        assert rows_inserted == 2
        assert rows[0]["run_id"] == 42
        assert rows[0]["source_system"] == "flexcube"
        assert rows[0]["source_object"] == "FCBOV.STTM_CUST_ACCOUNT"
        assert rows[0]["source_payload"] == expected_payload
        assert rows[0]["source_row_hash"] == hashlib.sha256(
            expected_payload.encode("utf-8")
        ).hexdigest()
        assert rows[1]["source_payload"] == json.dumps(
            {"office_account_number": "OFF002", "customer_code": "C002"},
            default=str,
            sort_keys=True,
        )
    finally:
        db.close()


def test_staging_writer_empty_rows_returns_zero(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_staging_tables(db)
        writer = StagingWriter(db)

        rows_inserted = writer.write_rows(
            staging_table="stg_flexcube_office_accounts",
            run_id=42,
            source_system="flexcube",
            source_object="FCBOV.STTM_CUST_ACCOUNT",
            rows=[],
        )

        assert rows_inserted == 0
        assert db.query_all("SELECT * FROM stg_flexcube_office_accounts") == []
    finally:
        db.close()


@pytest.mark.parametrize(
    "staging_table",
    [
        "office_accounts",
        "stg_flexcube-office-accounts",
        "stg_flexcube_office_accounts; DROP TABLE account_data",
    ],
)
def test_staging_writer_rejects_invalid_table_names(
    tmp_path: Path,
    staging_table: str,
) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    writer = StagingWriter(db)

    with pytest.raises(ValueError, match="Invalid staging table name"):
        writer.write_rows(
            staging_table=staging_table,
            run_id=42,
            source_system="flexcube",
            source_object="FCBOV.STTM_CUST_ACCOUNT",
            rows=[{"office_account_number": "OFF001"}],
        )

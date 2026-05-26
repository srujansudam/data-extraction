from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.extract.office_accounts import (
    OFFICE_ACCOUNTS_SQL,
    OfficeAccountsExtractionJob,
)
from data_extraction.tracking.runs import ExtractionRunTracker


class FakeSourceClient:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.executed_sql: str | None = None

    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.executed_sql = sql
        return self.rows


def create_test_run(db: SQLiteAdapter) -> int:
    run_tracker = ExtractionRunTracker(db)
    return run_tracker.start_run(
        run_type="daily",
        window_start=None,
        window_end=None,
        triggered_by="manual",
    )


def test_office_accounts_job_loads_rows_and_tracks_success(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)

        source_client = FakeSourceClient(
            rows=[
                {
                    "office_account_number": "OFF001",
                    "customer_code": "C001",
                    "office_account_name": "Office Account One",
                },
                {
                    "office_account_number": "OFF002",
                    "customer_code": "C002",
                    "office_account_name": "Office Account Two",
                },
            ]
        )

        job = OfficeAccountsExtractionJob(db=db, source_client=source_client)
        result = job.run(run_id=run_id, window_start=None, window_end=None)

        assert source_client.executed_sql == OFFICE_ACCOUNTS_SQL
        assert result.rows_extracted == 2
        assert result.rows_inserted == 2

        rows = db.query_all(
            """
            SELECT office_account_number, customer_code, office_account_name
            FROM office_accounts
            ORDER BY office_account_number
            """
        )

        assert rows == [
            {
                "office_account_number": "OFF001",
                "customer_code": "C001",
                "office_account_name": "Office Account One",
            },
            {
                "office_account_number": "OFF002",
                "customer_code": "C002",
                "office_account_name": "Office Account Two",
            },
        ]

        job_row = db.query_one(
            """
            SELECT status, rows_extracted, rows_inserted
            FROM extraction_job_run
            WHERE job_name = ?
            """,
            ["office_accounts"],
        )

        assert job_row is not None
        assert job_row["status"] == "completed"
        assert job_row["rows_extracted"] == 2
        assert job_row["rows_inserted"] == 2

        watermark = db.query_one(
            """
            SELECT job_name, source_system, target_table
            FROM extraction_job_watermark
            WHERE job_name = ?
            """,
            ["office_accounts"],
        )

        assert watermark is not None
        assert watermark["job_name"] == "office_accounts"
        assert watermark["source_system"] == "flexcube"
        assert watermark["target_table"] == "office_accounts"
    finally:
        db.close()


def test_office_accounts_job_refreshes_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        db.execute(
            """
            INSERT INTO office_accounts (
                office_account_number,
                customer_code,
                office_account_name
            )
            VALUES (?, ?, ?)
            """,
            ["OLD001", "OLD_CUST", "Old Office Account"],
        )
        db.commit()

        run_id = create_test_run(db)

        source_client = FakeSourceClient(
            rows=[
                {
                    "office_account_number": "NEW001",
                    "customer_code": "NEW_CUST",
                    "office_account_name": "New Office Account",
                },
            ]
        )

        job = OfficeAccountsExtractionJob(db=db, source_client=source_client)
        job.run(run_id=run_id, window_start=None, window_end=None)

        rows = db.query_all(
            """
            SELECT office_account_number, customer_code, office_account_name
            FROM office_accounts
            """
        )

        assert rows == [
            {
                "office_account_number": "NEW001",
                "customer_code": "NEW_CUST",
                "office_account_name": "New Office Account",
            }
        ]
    finally:
        db.close()
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.extract.loans import LOANS_SQL, LoansExtractionJob
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
        window_start="2026-05-25T00:00:00+02:00",
        window_end="2026-05-26T00:00:00+02:00",
        triggered_by="manual",
    )


def test_loans_job_loads_rows_and_tracks_success(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)

        source_client = FakeSourceClient(
            rows=[
                {
                    "account_number": "LN001",
                    "customer_code": "C001",
                    "product_lvl_6": "Term Loans",
                    "product_lvl_7": "Home Loan",
                    "drawdown_expiry_date": "2026-12-31",
                },
                {
                    "account_number": "LN002",
                    "customer_code": "C002",
                    "product_lvl_6": "Commercial Loans",
                    "product_lvl_7": "Business Loan",
                    "drawdown_expiry_date": "2027-06-30",
                },
            ]
        )

        job = LoansExtractionJob(db=db, source_client=source_client)
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        assert source_client.executed_sql == LOANS_SQL
        assert result.rows_extracted == 2
        assert result.rows_inserted == 2

        rows = db.query_all(
            """
            SELECT account_number, customer_code, product_lvl_6,
                   product_lvl_7, drawdown_expiry_date
            FROM loans
            ORDER BY account_number
            """
        )

        assert rows == [
            {
                "account_number": "LN001",
                "customer_code": "C001",
                "product_lvl_6": "Term Loans",
                "product_lvl_7": "Home Loan",
                "drawdown_expiry_date": "2026-12-31",
            },
            {
                "account_number": "LN002",
                "customer_code": "C002",
                "product_lvl_6": "Commercial Loans",
                "product_lvl_7": "Business Loan",
                "drawdown_expiry_date": "2027-06-30",
            },
        ]

        job_row = db.query_one(
            """
            SELECT status, rows_extracted, rows_inserted
            FROM extraction_job_run
            WHERE job_name = ?
            """,
            ["loans"],
        )

        assert job_row is not None
        assert job_row["status"] == "completed"
        assert job_row["rows_extracted"] == 2
        assert job_row["rows_inserted"] == 2
    finally:
        db.close()


def test_loans_job_refreshes_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        db.execute(
            """
            INSERT INTO loans (
                account_number,
                customer_code,
                product_lvl_6,
                product_lvl_7,
                drawdown_expiry_date
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ["OLD001", "OLD_CUST", "Old Level 6", "Old Level 7", "2026-01-01"],
        )
        db.commit()
        run_id = create_test_run(db)

        source_client = FakeSourceClient(
            rows=[
                {
                    "account_number": "LN001",
                    "customer_code": "C001",
                    "product_lvl_6": "Term Loans",
                    "product_lvl_7": "Home Loan",
                    "drawdown_expiry_date": "2026-12-31",
                },
            ]
        )

        job = LoansExtractionJob(db=db, source_client=source_client)
        job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all(
            """
            SELECT account_number, customer_code, product_lvl_6,
                   product_lvl_7, drawdown_expiry_date
            FROM loans
            """
        )

        assert rows == [
            {
                "account_number": "LN001",
                "customer_code": "C001",
                "product_lvl_6": "Term Loans",
                "product_lvl_7": "Home Loan",
                "drawdown_expiry_date": "2026-12-31",
            }
        ]
    finally:
        db.close()

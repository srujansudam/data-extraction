from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.extract.eom_book_balance import (
    EOM_BOOK_BALANCE_SQL,
    EomBookBalanceExtractionJob,
)
from data_extraction.tracking.runs import ExtractionRunTracker


def test_eom_book_balance_sql_uses_rolling_24_month_filter() -> None:
    assert "ADD_MONTHS(TRUNC(SYSDATE), -24)" in EOM_BOOK_BALANCE_SQL


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


def test_eom_book_balance_job_loads_rows_and_tracks_success(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)

        source_client = FakeSourceClient(
            rows=[
                {
                    "eom_date": "2026-04-30",
                    "customer_code": "C001",
                    "account_number": "ACC001",
                    "product_lvl_7": "Current Account",
                    "book_balance": 1500.25,
                },
                {
                    "eom_date": "2026-04-30",
                    "customer_code": "C002",
                    "account_number": "ACC002",
                    "product_lvl_7": "Savings Account",
                    "book_balance": 2750.75,
                },
            ]
        )

        job = EomBookBalanceExtractionJob(db=db, source_client=source_client)
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        assert source_client.executed_sql == EOM_BOOK_BALANCE_SQL
        assert result.rows_extracted == 2
        assert result.rows_inserted == 2

        rows = db.query_all(
            """
            SELECT eom_date, customer_code, account_number, product_lvl_7, book_balance
            FROM eom_book_balance
            ORDER BY account_number
            """
        )

        assert rows == [
            {
                "eom_date": "2026-04-30",
                "customer_code": "C001",
                "account_number": "ACC001",
                "product_lvl_7": "Current Account",
                "book_balance": 1500.25,
            },
            {
                "eom_date": "2026-04-30",
                "customer_code": "C002",
                "account_number": "ACC002",
                "product_lvl_7": "Savings Account",
                "book_balance": 2750.75,
            },
        ]

        job_row = db.query_one(
            """
            SELECT status, rows_extracted, rows_inserted
            FROM extraction_job_run
            WHERE job_name = ?
            """,
            ["eom_book_balance"],
        )

        assert job_row is not None
        assert job_row["status"] == "completed"
        assert job_row["rows_extracted"] == 2
        assert job_row["rows_inserted"] == 2
    finally:
        db.close()


def test_eom_book_balance_job_deduplicates_identical_source_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)

        source_client = FakeSourceClient(
            rows=[
                {
                    "eom_date": "2026-04-30",
                    "customer_code": "C001",
                    "account_number": "ACC001",
                    "product_lvl_7": "Current Account",
                    "book_balance": 1500.25,
                },
                {
                    "eom_date": "2026-04-30",
                    "customer_code": "C001",
                    "account_number": "ACC001",
                    "product_lvl_7": "Current Account",
                    "book_balance": 1500.25,
                },
            ]
        )

        job = EomBookBalanceExtractionJob(db=db, source_client=source_client)
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all("SELECT account_number FROM eom_book_balance")

        assert result.rows_extracted == 2
        assert result.rows_inserted == 1
        assert rows == [{"account_number": "ACC001"}]
    finally:
        db.close()


def test_eom_book_balance_job_replaces_incoming_keys(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        db.execute_many(
            """
            INSERT INTO eom_book_balance (
                eom_date,
                customer_code,
                account_number,
                product_lvl_7,
                book_balance
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ["2026-04-30", "C001", "ACC001", "Old Product", 99.0],
                ["2026-04-30", "C999", "KEEP", "Savings Account", 50.0],
            ],
        )
        db.commit()
        run_id = create_test_run(db)

        source_client = FakeSourceClient(
            rows=[
                {
                    "eom_date": "2026-04-30",
                    "customer_code": "C001",
                    "account_number": "ACC001",
                    "product_lvl_7": "Current Account",
                    "book_balance": 1500.25,
                },
                {
                    "eom_date": "2026-04-30",
                    "customer_code": "C001",
                    "account_number": "ACC001",
                    "product_lvl_7": "Current Account",
                    "book_balance": 2000.00,
                },
            ]
        )

        job = EomBookBalanceExtractionJob(db=db, source_client=source_client)
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all(
            """
            SELECT eom_date, customer_code, account_number, product_lvl_7, book_balance
            FROM eom_book_balance
            ORDER BY account_number
            """
        )

        assert result.rows_extracted == 2
        assert result.rows_inserted == 1
        assert rows == [
            {
                "eom_date": "2026-04-30",
                "customer_code": "C001",
                "account_number": "ACC001",
                "product_lvl_7": "Current Account",
                "book_balance": 1500.25,
            },
            {
                "eom_date": "2026-04-30",
                "customer_code": "C999",
                "account_number": "KEEP",
                "product_lvl_7": "Savings Account",
                "book_balance": 50.0,
            },
        ]
    finally:
        db.close()

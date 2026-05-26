from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.extract.exchange_rate import (
    EXCHANGE_RATE_SQL,
    ExchangeRateExtractionJob,
)
from data_extraction.tracking.runs import ExtractionRunTracker


class FakeSourceClient:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.executed_sql: str | None = None
        self.executed_params: Iterable[Any] | None = None

    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.executed_sql = sql
        self.executed_params = params
        return self.rows


def create_test_run(db: SQLiteAdapter) -> int:
    run_tracker = ExtractionRunTracker(db)
    return run_tracker.start_run(
        run_type="daily",
        window_start="2026-05-25T00:00:00+02:00",
        window_end="2026-05-26T00:00:00+02:00",
        triggered_by="manual",
    )


def test_exchange_rate_job_loads_rows_and_tracks_success(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)

        source_client = FakeSourceClient(
            rows=[
                {
                    "transaction_id": "FX001",
                    "customer_code": "C001",
                    "base_currency": "EUR",
                    "transaction_type": "SPOT",
                    "branch": "001",
                    "amount": 100.0,
                    "transaction_currency": "USD",
                    "exchange_rate": 1.08,
                    "middle_rate": 1.07,
                    "transaction_date": "2026-05-25",
                },
                {
                    "transaction_id": "FX002",
                    "customer_code": "C002",
                    "base_currency": "EUR",
                    "transaction_type": "SPOT",
                    "branch": "002",
                    "amount": 250.0,
                    "transaction_currency": "GBP",
                    "exchange_rate": 0.86,
                    "middle_rate": 0.85,
                    "transaction_date": "2026-05-25",
                },
            ]
        )

        job = ExchangeRateExtractionJob(db=db, source_client=source_client)
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        assert source_client.executed_sql == EXCHANGE_RATE_SQL
        assert source_client.executed_params == ["2026-05-25", "2026-05-26"]
        assert result.rows_extracted == 2
        assert result.rows_inserted == 2

        rows = db.query_all(
            """
            SELECT transaction_id, customer_code, base_currency, transaction_type,
                   branch, amount, transaction_currency, exchange_rate,
                   middle_rate, transaction_date
            FROM exchange_rate
            ORDER BY transaction_id
            """
        )

        assert rows == [
            {
                "transaction_id": "FX001",
                "customer_code": "C001",
                "base_currency": "EUR",
                "transaction_type": "SPOT",
                "branch": "001",
                "amount": 100.0,
                "transaction_currency": "USD",
                "exchange_rate": 1.08,
                "middle_rate": 1.07,
                "transaction_date": "2026-05-25",
            },
            {
                "transaction_id": "FX002",
                "customer_code": "C002",
                "base_currency": "EUR",
                "transaction_type": "SPOT",
                "branch": "002",
                "amount": 250.0,
                "transaction_currency": "GBP",
                "exchange_rate": 0.86,
                "middle_rate": 0.85,
                "transaction_date": "2026-05-25",
            },
        ]

        job_row = db.query_one(
            """
            SELECT status, rows_extracted, rows_inserted
            FROM extraction_job_run
            WHERE job_name = ?
            """,
            ["exchange_rate"],
        )

        assert job_row is not None
        assert job_row["status"] == "completed"
        assert job_row["rows_extracted"] == 2
        assert job_row["rows_inserted"] == 2
    finally:
        db.close()


def test_exchange_rate_job_replaces_incoming_transaction_ids(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        db.execute_many(
            """
            INSERT INTO exchange_rate (
                transaction_id,
                customer_code,
                base_currency,
                transaction_type,
                branch,
                amount,
                transaction_currency,
                exchange_rate,
                middle_rate,
                transaction_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ["FX001", "OLD", "EUR", "OLD", "999", 1.0, "USD", 1.0, 1.0, "2026-05-24"],
                ["KEEP", "C999", "EUR", "SPOT", "999", 5.0, "USD", 1.1, 1.0, "2026-05-24"],
            ],
        )
        db.commit()
        run_id = create_test_run(db)

        source_client = FakeSourceClient(
            rows=[
                {
                    "transaction_id": "FX001",
                    "customer_code": "C001",
                    "base_currency": "EUR",
                    "transaction_type": "SPOT",
                    "branch": "001",
                    "amount": 100.0,
                    "transaction_currency": "USD",
                    "exchange_rate": 1.08,
                    "middle_rate": 1.07,
                    "transaction_date": "2026-05-25",
                },
                {
                    "transaction_id": "FX002",
                    "customer_code": "C002",
                    "base_currency": "EUR",
                    "transaction_type": "SPOT",
                    "branch": "002",
                    "amount": 250.0,
                    "transaction_currency": "GBP",
                    "exchange_rate": 0.86,
                    "middle_rate": 0.85,
                    "transaction_date": "2026-05-25",
                },
            ]
        )

        job = ExchangeRateExtractionJob(db=db, source_client=source_client)
        job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all(
            """
            SELECT transaction_id, customer_code, amount
            FROM exchange_rate
            ORDER BY transaction_id
            """
        )

        assert rows == [
            {"transaction_id": "FX001", "customer_code": "C001", "amount": 100.0},
            {"transaction_id": "FX002", "customer_code": "C002", "amount": 250.0},
            {"transaction_id": "KEEP", "customer_code": "C999", "amount": 5.0},
        ]
    finally:
        db.close()


@pytest.mark.parametrize(
    ("window_start", "window_end"),
    [
        (None, "2026-05-26T00:00:00+02:00"),
        ("2026-05-25T00:00:00+02:00", None),
    ],
)
def test_exchange_rate_job_requires_window(
    tmp_path: Path,
    window_start: str | None,
    window_end: str | None,
) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    source_client = FakeSourceClient(rows=[])
    job = ExchangeRateExtractionJob(db=db, source_client=source_client)

    with pytest.raises(ValueError, match="requires window_start and window_end"):
        job.execute(window_start=window_start, window_end=window_end)

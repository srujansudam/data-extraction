from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.extract.credit_cards import (
    CREDIT_CARDS_SQL,
    CreditCardsExtractionJob,
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


def test_credit_cards_job_loads_rows_with_null_amount(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        source_client = FakeSourceClient(
            rows=[
                {
                    "transaction_reference": "301ABC",
                    "user_code": "USER1",
                    "date": "2026-05-25",
                    "customer_code": "C001",
                    "branch_code": "301",
                    "amount": 999.0,
                    "credit_card_number": "411111******1111",
                }
            ]
        )

        job = CreditCardsExtractionJob(db=db, source_client=source_client)
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        assert source_client.executed_sql == CREDIT_CARDS_SQL
        assert source_client.executed_params == ["2026-05-25", "2026-05-26"]
        assert result.rows_extracted == 1
        assert result.rows_inserted == 1

        rows = db.query_all(
            """
            SELECT transaction_reference, user_code, date, customer_code,
                   branch_code, amount, credit_card_number
            FROM credit_cards
            """
        )

        assert rows == [
            {
                "transaction_reference": "301ABC",
                "user_code": "USER1",
                "date": "2026-05-25",
                "customer_code": "C001",
                "branch_code": "301",
                "amount": None,
                "credit_card_number": "411111******1111",
            }
        ]
    finally:
        db.close()


def test_credit_cards_job_replaces_incoming_transaction_references(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        db.execute_many(
            """
            INSERT INTO credit_cards (
                transaction_reference,
                user_code,
                date,
                customer_code,
                branch_code,
                amount,
                credit_card_number
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ["301ABC", "OLD", "2026-05-24", "OLD", "301", None, "OLD_CARD"],
                ["KEEP", "USER9", "2026-05-24", "C999", "302", None, "KEEP_CARD"],
            ],
        )
        db.commit()
        run_id = create_test_run(db)
        source_client = FakeSourceClient(
            rows=[
                {
                    "transaction_reference": "301ABC",
                    "user_code": "USER1",
                    "date": "2026-05-25",
                    "customer_code": "C001",
                    "branch_code": "301",
                    "amount": 123.0,
                    "credit_card_number": "NEW_CARD",
                }
            ]
        )

        job = CreditCardsExtractionJob(db=db, source_client=source_client)
        job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all(
            """
            SELECT transaction_reference, user_code, amount, credit_card_number
            FROM credit_cards
            ORDER BY transaction_reference
            """
        )

        assert rows == [
            {
                "transaction_reference": "301ABC",
                "user_code": "USER1",
                "amount": None,
                "credit_card_number": "NEW_CARD",
            },
            {
                "transaction_reference": "KEEP",
                "user_code": "USER9",
                "amount": None,
                "credit_card_number": "KEEP_CARD",
            },
        ]
    finally:
        db.close()


def test_credit_cards_job_allows_no_source_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        source_client = FakeSourceClient(rows=[])
        job = CreditCardsExtractionJob(db=db, source_client=source_client)

        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        assert result.rows_extracted == 0
        assert result.rows_inserted == 0
        assert db.query_all("SELECT * FROM credit_cards") == []
    finally:
        db.close()


@pytest.mark.parametrize(
    ("window_start", "window_end"),
    [
        (None, "2026-05-26T00:00:00+02:00"),
        ("2026-05-25T00:00:00+02:00", None),
    ],
)
def test_credit_cards_job_requires_window(
    tmp_path: Path,
    window_start: str | None,
    window_end: str | None,
) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    source_client = FakeSourceClient(rows=[])
    job = CreditCardsExtractionJob(db=db, source_client=source_client)

    with pytest.raises(ValueError, match="requires window_start and window_end"):
        job.execute(window_start=window_start, window_end=window_end)

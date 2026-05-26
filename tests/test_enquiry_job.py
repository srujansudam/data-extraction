from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.extract.enquiry import ENQUIRY_SQL, EnquiryExtractionJob
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


def test_enquiry_sql_shape() -> None:
    assert "UNION ALL" in ENQUIRY_SQL
    assert "EXECUTEQUERY" in ENQUIRY_SQL
    assert "resp_xml" not in ENQUIRY_SQL.lower()


def test_enquiry_job_loads_rows_and_tracks_success(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        source_client = FakeSourceClient(
            rows=[
                {
                    "user_code": "USER1",
                    "function_id": "STDCIF",
                    "start_time": "2026-05-25T09:00:00",
                    "action_time": "2026-05-25T09:01:00",
                    "terminal_id": "TERM1",
                    "branch_code": "001",
                    "description": "Customer Input",
                    "action": "EXECUTEQUERY",
                    "pkvals": "CUSTOMER001M",
                    "breadcrumbs": "Main -> Customer -> Summary",
                    "error_msg": None,
                }
            ]
        )

        job = EnquiryExtractionJob(db=db, source_client=source_client)
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        assert source_client.executed_sql == ENQUIRY_SQL
        assert source_client.executed_params == ["2026-05-25", "2026-05-26"]
        assert result.rows_extracted == 1
        assert result.rows_inserted == 1

        rows = db.query_all(
            """
            SELECT user_code, function_id, start_time, action_time, terminal_id,
                   branch_code, description, action, pkvals, breadcrumbs, error_msg
            FROM enquiry
            """
        )

        assert rows == [
            {
                "user_code": "USER1",
                "function_id": "STDCIF",
                "start_time": "2026-05-25T09:00:00",
                "action_time": "2026-05-25T09:01:00",
                "terminal_id": "TERM1",
                "branch_code": "001",
                "description": "Customer Input",
                "action": "EXECUTEQUERY",
                "pkvals": "CUSTOMER001M",
                "breadcrumbs": "Main -> Customer -> Summary",
                "error_msg": None,
            }
        ]
    finally:
        db.close()


def test_enquiry_job_replaces_incoming_unique_keys(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        db.execute_many(
            """
            INSERT INTO enquiry (
                user_code,
                function_id,
                start_time,
                action_time,
                terminal_id,
                branch_code,
                description,
                action,
                pkvals,
                breadcrumbs,
                error_msg
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                [
                    "USER1",
                    "STDCIF",
                    "2026-05-25T09:00:00",
                    "OLD",
                    "OLD",
                    "001",
                    "Old",
                    "EXECUTEQUERY",
                    "OLD",
                    "Old",
                    "Old",
                ],
                [
                    "KEEP",
                    "STDCUSUM",
                    "2026-05-25T10:00:00",
                    "2026-05-25T10:01:00",
                    "TERM9",
                    "009",
                    "Keep",
                    "EXECUTEQUERY",
                    "KEEPVALN",
                    "Keep",
                    None,
                ],
            ],
        )
        db.commit()
        run_id = create_test_run(db)
        source_client = FakeSourceClient(
            rows=[
                {
                    "user_code": "USER1",
                    "function_id": "STDCIF",
                    "start_time": "2026-05-25T09:00:00",
                    "action_time": "2026-05-25T09:01:00",
                    "terminal_id": "TERM1",
                    "branch_code": "001",
                    "description": "Customer Input",
                    "action": "EXECUTEQUERY",
                    "pkvals": "CUSTOMER001M",
                    "breadcrumbs": "Main -> Customer -> Summary",
                    "error_msg": None,
                }
            ]
        )

        job = EnquiryExtractionJob(db=db, source_client=source_client)
        job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all(
            """
            SELECT user_code, function_id, start_time, action_time, pkvals
            FROM enquiry
            ORDER BY user_code
            """
        )

        assert rows == [
            {
                "user_code": "KEEP",
                "function_id": "STDCUSUM",
                "start_time": "2026-05-25T10:00:00",
                "action_time": "2026-05-25T10:01:00",
                "pkvals": "KEEPVALN",
            },
            {
                "user_code": "USER1",
                "function_id": "STDCIF",
                "start_time": "2026-05-25T09:00:00",
                "action_time": "2026-05-25T09:01:00",
                "pkvals": "CUSTOMER001M",
            },
        ]
    finally:
        db.close()


def test_enquiry_job_allows_no_source_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        source_client = FakeSourceClient(rows=[])
        job = EnquiryExtractionJob(db=db, source_client=source_client)

        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        assert result.rows_extracted == 0
        assert result.rows_inserted == 0
        assert db.query_all("SELECT * FROM enquiry") == []
    finally:
        db.close()


@pytest.mark.parametrize(
    ("window_start", "window_end"),
    [
        (None, "2026-05-26T00:00:00+02:00"),
        ("2026-05-25T00:00:00+02:00", None),
    ],
)
def test_enquiry_job_requires_window(
    tmp_path: Path,
    window_start: str | None,
    window_end: str | None,
) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    source_client = FakeSourceClient(rows=[])
    job = EnquiryExtractionJob(db=db, source_client=source_client)

    with pytest.raises(ValueError, match="requires window_start and window_end"):
        job.execute(window_start=window_start, window_end=window_end)

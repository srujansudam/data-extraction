from __future__ import annotations

from pathlib import Path

import pytest

from data_extraction.db.schema import create_tracking_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.tracking.runs import ExtractionRunTracker
from data_extraction.transform.base import BaseTransformJob, TransformResult


class SuccessfulDummyTransformJob(BaseTransformJob):
    job_name = "dummy_transform_success"
    target_table = "customer_data"

    def execute_transform(
        self,
        window_start: str | None,
        window_end: str | None,
    ) -> TransformResult:
        assert window_start == "2026-05-25T00:00:00+02:00"
        assert window_end == "2026-05-26T00:00:00+02:00"

        return TransformResult(
            rows_read=10,
            rows_inserted=6,
            rows_updated=3,
            rows_rejected=1,
        )


class FailingDummyTransformJob(BaseTransformJob):
    job_name = "dummy_transform_failure"
    target_table = "customer_data"

    def execute_transform(
        self,
        window_start: str | None,
        window_end: str | None,
    ) -> TransformResult:
        raise ValueError("dummy transform failed")


def create_test_run(db: SQLiteAdapter) -> int:
    run_tracker = ExtractionRunTracker(db)
    return run_tracker.start_run(
        run_type="daily",
        window_start="2026-05-25T00:00:00+02:00",
        window_end="2026-05-26T00:00:00+02:00",
        triggered_by="manual",
    )


def test_successful_transform_job_is_tracked(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)
        run_id = create_test_run(db)

        job = SuccessfulDummyTransformJob(db)
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        assert result.rows_read == 10
        assert result.rows_inserted == 6
        assert result.rows_updated == 3
        assert result.rows_rejected == 1

        job_row = db.query_one(
            """
            SELECT job_name, source_system, target_table, status, rows_extracted,
                   rows_inserted, rows_updated, rows_rejected
            FROM extraction_job_run
            WHERE job_name = ?
            """,
            ["dummy_transform_success"],
        )

        assert job_row is not None
        assert job_row["source_system"] == "internal"
        assert job_row["target_table"] == "customer_data"
        assert job_row["status"] == "completed"
        assert job_row["rows_extracted"] == 10
        assert job_row["rows_inserted"] == 6
        assert job_row["rows_updated"] == 3
        assert job_row["rows_rejected"] == 1

        watermark = db.query_one(
            """
            SELECT job_name, source_system, target_table
            FROM extraction_job_watermark
            WHERE job_name = ?
            """,
            ["dummy_transform_success"],
        )

        assert watermark is not None
        assert watermark["job_name"] == "dummy_transform_success"
        assert watermark["source_system"] == "internal"
        assert watermark["target_table"] == "customer_data"
    finally:
        db.close()


def test_failed_transform_job_is_tracked_and_logs_error(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)
        run_id = create_test_run(db)

        job = FailingDummyTransformJob(db)

        with pytest.raises(ValueError, match="dummy transform failed"):
            job.run(
                run_id=run_id,
                window_start="2026-05-25T00:00:00+02:00",
                window_end="2026-05-26T00:00:00+02:00",
            )

        job_row = db.query_one(
            """
            SELECT job_name, source_system, status, error_message
            FROM extraction_job_run
            WHERE job_name = ?
            """,
            ["dummy_transform_failure"],
        )

        assert job_row is not None
        assert job_row["source_system"] == "internal"
        assert job_row["status"] == "failed"
        assert job_row["error_message"] == "dummy transform failed"

        error_row = db.query_one(
            """
            SELECT job_name, source_system, error_type, error_message
            FROM extraction_error_log
            WHERE job_name = ?
            """,
            ["dummy_transform_failure"],
        )

        assert error_row is not None
        assert error_row["job_name"] == "dummy_transform_failure"
        assert error_row["source_system"] == "internal"
        assert error_row["error_type"] == "ValueError"
        assert error_row["error_message"] == "dummy transform failed"
    finally:
        db.close()

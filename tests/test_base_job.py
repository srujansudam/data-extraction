from pathlib import Path

import pytest

from data_extraction.db.schema import create_tracking_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult
from data_extraction.tracking.runs import ExtractionRunTracker


class SuccessfulDummyJob(BaseExtractionJob):
    job_name = "dummy_success"
    source_system = "test_source"
    target_table = "test_table"

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        assert window_start == "2026-05-25T00:00:00+02:00"
        assert window_end == "2026-05-26T00:00:00+02:00"

        return JobResult(
            rows_extracted=10,
            rows_inserted=8,
            rows_updated=2,
            rows_rejected=0,
        )


class FailingDummyJob(BaseExtractionJob):
    job_name = "dummy_failure"
    source_system = "test_source"
    target_table = "test_table"

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        raise ValueError("dummy job failed")


class SecretFailingDummyJob(BaseExtractionJob):
    job_name = "dummy_secret_failure"
    source_system = "test_source"
    target_table = "test_table"

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        raise ValueError("dummy job failed password=super-secret-password")


def create_test_run(db: SQLiteAdapter) -> int:
    run_tracker = ExtractionRunTracker(db)
    return run_tracker.start_run(
        run_type="daily",
        window_start="2026-05-25T00:00:00+02:00",
        window_end="2026-05-26T00:00:00+02:00",
        triggered_by="manual",
    )


def test_successful_base_job_tracks_job_and_watermark(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)
        run_id = create_test_run(db)

        job = SuccessfulDummyJob(db)
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        assert result.rows_extracted == 10
        assert result.rows_inserted == 8
        assert result.rows_updated == 2
        assert result.rows_rejected == 0

        job_row = db.query_one(
            """
            SELECT job_name, status, rows_extracted, rows_inserted, rows_updated, rows_rejected
            FROM extraction_job_run
            WHERE job_name = ?
            """,
            ["dummy_success"],
        )

        assert job_row is not None
        assert job_row["status"] == "completed"
        assert job_row["rows_extracted"] == 10
        assert job_row["rows_inserted"] == 8
        assert job_row["rows_updated"] == 2
        assert job_row["rows_rejected"] == 0

        watermark = db.query_one(
            """
            SELECT job_name, source_system, target_table,
                   last_successful_window_start, last_successful_window_end
            FROM extraction_job_watermark
            WHERE job_name = ?
            """,
            ["dummy_success"],
        )

        assert watermark is not None
        assert watermark["job_name"] == "dummy_success"
        assert watermark["source_system"] == "test_source"
        assert watermark["target_table"] == "test_table"
        assert watermark["last_successful_window_start"] == "2026-05-25T00:00:00+02:00"
        assert watermark["last_successful_window_end"] == "2026-05-26T00:00:00+02:00"
    finally:
        db.close()


def test_failing_base_job_tracks_failure_and_error_log(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)
        run_id = create_test_run(db)

        job = FailingDummyJob(db)

        with pytest.raises(ValueError, match="dummy job failed"):
            job.run(
                run_id=run_id,
                window_start="2026-05-25T00:00:00+02:00",
                window_end="2026-05-26T00:00:00+02:00",
            )

        job_row = db.query_one(
            """
            SELECT job_name, status, error_message
            FROM extraction_job_run
            WHERE job_name = ?
            """,
            ["dummy_failure"],
        )

        assert job_row is not None
        assert job_row["status"] == "failed"
        assert job_row["error_message"] == "dummy job failed"

        error_row = db.query_one(
            """
            SELECT job_name, source_system, error_type, error_message
            FROM extraction_error_log
            WHERE job_name = ?
            """,
            ["dummy_failure"],
        )

        assert error_row is not None
        assert error_row["job_name"] == "dummy_failure"
        assert error_row["source_system"] == "test_source"
        assert error_row["error_type"] == "ValueError"
        assert error_row["error_message"] == "dummy job failed"
    finally:
        db.close()


def test_failing_base_job_logs_sanitized_error(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)
        run_id = create_test_run(db)

        job = SecretFailingDummyJob(db)

        with pytest.raises(ValueError, match="super-secret-password"):
            job.run(run_id=run_id, window_start=None, window_end=None)

        log_text = caplog.text
        error_row = db.query_one(
            """
            SELECT error_message
            FROM extraction_error_log
            WHERE job_name = ?
            """,
            ["dummy_secret_failure"],
        )

        assert error_row is not None
        assert error_row["error_message"] == "dummy job failed password=[REDACTED]"
        assert "dummy job failed password=[REDACTED]" in log_text
        assert "super-secret-password" not in log_text
    finally:
        db.close()

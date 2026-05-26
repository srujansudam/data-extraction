from pathlib import Path

import pytest

from data_extraction.db.schema import create_tracking_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult
from data_extraction.jobs.runner import ExtractionRunner


class SuccessfulRunnerJob(BaseExtractionJob):
    job_name = "runner_success"
    source_system = "test_source"
    target_table = "test_table"

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        return JobResult(rows_extracted=5, rows_inserted=5)


class FailingRunnerJob(BaseExtractionJob):
    job_name = "runner_failure"
    source_system = "test_source"
    target_table = "test_table"

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        raise RuntimeError("runner job failed")


def test_extraction_runner_completes_successful_run(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)

        runner = ExtractionRunner(db)
        job = SuccessfulRunnerJob(db)

        result = runner.run_jobs(
            run_type="daily",
            jobs=[job],
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
            triggered_by="manual",
        )

        assert result.run_id == 1
        assert result.job_results["runner_success"].rows_extracted == 5

        run_row = db.query_one(
            """
            SELECT run_type, status, window_start, window_end
            FROM extraction_run
            WHERE run_id = ?
            """,
            [result.run_id],
        )

        assert run_row is not None
        assert run_row["run_type"] == "daily"
        assert run_row["status"] == "completed"
        assert run_row["window_start"] == "2026-05-25T00:00:00+02:00"
        assert run_row["window_end"] == "2026-05-26T00:00:00+02:00"
    finally:
        db.close()


def test_extraction_runner_fails_run_when_job_fails(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)

        runner = ExtractionRunner(db)
        job = FailingRunnerJob(db)

        with pytest.raises(RuntimeError, match="runner job failed"):
            runner.run_jobs(
                run_type="daily",
                jobs=[job],
                window_start="2026-05-25T00:00:00+02:00",
                window_end="2026-05-26T00:00:00+02:00",
                triggered_by="manual",
            )

        run_row = db.query_one(
            """
            SELECT status, notes
            FROM extraction_run
            WHERE run_id = ?
            """,
            [1],
        )

        assert run_row is not None
        assert run_row["status"] == "failed"
        assert run_row["notes"] == "runner job failed"

        error_row = db.query_one(
            """
            SELECT error_type, error_message
            FROM extraction_error_log
            WHERE run_id = ?
              AND job_run_id IS NULL
            """,
            [1],
        )

        assert error_row is not None
        assert error_row["error_type"] == "RuntimeError"
        assert error_row["error_message"] == "runner job failed"
    finally:
        db.close()
from __future__ import annotations

from pathlib import Path

import pytest

from data_extraction.db.schema import create_tracking_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult
from data_extraction.pipeline.runner import PipelineRunner
from data_extraction.transform.base import BaseTransformJob, TransformResult


class RecordingStagingJob(BaseExtractionJob):
    job_name = "recording_staging"
    source_system = "test_source"
    target_table = "stg_test_source"

    def __init__(
        self,
        db: SQLiteAdapter,
        execution_log: list[str],
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(db=db, timezone=timezone)
        self.execution_log = execution_log

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        self.execution_log.append(f"{self.job_name}:{window_start}:{window_end}")
        return JobResult(rows_extracted=2, rows_inserted=2)


class FailingStagingJob(BaseExtractionJob):
    job_name = "failing_staging"
    source_system = "test_source"
    target_table = "stg_test_source"

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        raise RuntimeError("staging failed")


class RecordingTransformJob(BaseTransformJob):
    job_name = "recording_transform"
    target_table = "final_test"

    def __init__(
        self,
        db: SQLiteAdapter,
        execution_log: list[str],
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(db=db, timezone=timezone)
        self.execution_log = execution_log

    def execute_transform(
        self,
        run_id: int,
        window_start: str | None,
        window_end: str | None,
    ) -> TransformResult:
        self.execution_log.append(f"{self.job_name}:{run_id}:{window_start}:{window_end}")
        return TransformResult(rows_read=2, rows_inserted=1)


class FailingTransformJob(BaseTransformJob):
    job_name = "failing_transform"
    target_table = "final_test"

    def execute_transform(
        self,
        run_id: int,
        window_start: str | None,
        window_end: str | None,
    ) -> TransformResult:
        raise RuntimeError("transform failed")


def open_tracking_db(tmp_path: Path) -> SQLiteAdapter:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()
    create_tracking_tables(db)
    return db


def test_successful_pipeline_tracks_completed_run_and_preserves_order(tmp_path: Path) -> None:
    db = open_tracking_db(tmp_path)

    try:
        execution_log: list[str] = []
        runner = PipelineRunner(db)
        run_id = runner.run_pipeline(
            run_type="daily",
            staging_jobs=[RecordingStagingJob(db, execution_log)],
            transform_jobs=[RecordingTransformJob(db, execution_log)],
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
            triggered_by="manual",
            notes="pipeline test",
        )

        run_row = db.query_one("SELECT status, notes FROM extraction_run WHERE run_id = ?", [run_id])
        job_rows = db.query_all(
            "SELECT job_name, status FROM extraction_job_run ORDER BY job_run_id"
        )

        assert run_row is not None
        assert run_row["status"] == "completed"
        assert run_row["notes"] == "pipeline test"
        assert [row["job_name"] for row in job_rows] == [
            "recording_staging",
            "recording_transform",
        ]
        assert [row["status"] for row in job_rows] == ["completed", "completed"]
        assert execution_log == [
            "recording_staging:2026-05-25T00:00:00+02:00:2026-05-26T00:00:00+02:00",
            (
                "recording_transform:"
                f"{run_id}:"
                "2026-05-25T00:00:00+02:00:"
                "2026-05-26T00:00:00+02:00"
            ),
        ]
    finally:
        db.close()


def test_failed_staging_job_marks_run_failed_and_logs_error(tmp_path: Path) -> None:
    db = open_tracking_db(tmp_path)

    try:
        runner = PipelineRunner(db)

        with pytest.raises(RuntimeError, match="staging failed"):
            runner.run_pipeline(
                run_type="daily",
                staging_jobs=[FailingStagingJob(db)],
                transform_jobs=[RecordingTransformJob(db, [])],
                window_start="2026-05-25T00:00:00+02:00",
                window_end="2026-05-26T00:00:00+02:00",
            )

        run_row = db.query_one("SELECT run_id, status, notes FROM extraction_run")
        assert run_row is not None
        assert run_row["status"] == "failed"
        assert run_row["notes"] == "staging failed"

        error_rows = db.query_all(
            """
            SELECT run_id, job_name, error_type, error_message
            FROM extraction_error_log
            ORDER BY error_id
            """
        )
        assert error_rows[-1] == {
            "run_id": run_row["run_id"],
            "job_name": None,
            "error_type": "RuntimeError",
            "error_message": "staging failed",
        }

        transform_row = db.query_one(
            "SELECT job_name FROM extraction_job_run WHERE job_name = ?",
            ["recording_transform"],
        )
        assert transform_row is None
    finally:
        db.close()


def test_failed_transform_job_marks_run_failed_and_logs_error(tmp_path: Path) -> None:
    db = open_tracking_db(tmp_path)

    try:
        execution_log: list[str] = []
        runner = PipelineRunner(db)

        with pytest.raises(RuntimeError, match="transform failed"):
            runner.run_pipeline(
                run_type="daily",
                staging_jobs=[RecordingStagingJob(db, execution_log)],
                transform_jobs=[FailingTransformJob(db)],
                window_start="2026-05-25T00:00:00+02:00",
                window_end="2026-05-26T00:00:00+02:00",
            )

        run_row = db.query_one("SELECT run_id, status, notes FROM extraction_run")
        job_rows = db.query_all(
            "SELECT job_name, status FROM extraction_job_run ORDER BY job_run_id"
        )
        assert run_row is not None
        assert run_row["status"] == "failed"
        assert run_row["notes"] == "transform failed"
        assert job_rows == [
            {"job_name": "recording_staging", "status": "completed"},
            {"job_name": "failing_transform", "status": "failed"},
        ]

        error_rows = db.query_all(
            """
            SELECT run_id, job_name, error_type, error_message
            FROM extraction_error_log
            ORDER BY error_id
            """
        )
        assert error_rows[-1] == {
            "run_id": run_row["run_id"],
            "job_name": None,
            "error_type": "RuntimeError",
            "error_message": "transform failed",
        }
    finally:
        db.close()

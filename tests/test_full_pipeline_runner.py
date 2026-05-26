from __future__ import annotations

from pathlib import Path

import pytest

from data_extraction.db.schema import create_tracking_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult
from data_extraction.pipeline.full_runner import FullPipelineRunner
from data_extraction.transform.base import BaseTransformJob, TransformResult


class RecordingExtractionJob(BaseExtractionJob):
    source_system = "test_source"
    target_table = "test_target"

    def __init__(
        self,
        db: SQLiteAdapter,
        job_name: str,
        phase: str,
        execution_log: list[str],
    ) -> None:
        super().__init__(db=db)
        self.job_name = job_name
        self.phase = phase
        self.execution_log = execution_log

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        self.execution_log.append(f"{self.phase}:{self.job_name}")
        return JobResult(rows_extracted=1, rows_inserted=1)


class FailingExtractionJob(BaseExtractionJob):
    source_system = "test_source"
    target_table = "test_target"

    def __init__(self, db: SQLiteAdapter, job_name: str, error_message: str) -> None:
        super().__init__(db=db)
        self.job_name = job_name
        self.error_message = error_message

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        raise RuntimeError(self.error_message)


class RecordingTransformJob(BaseTransformJob):
    target_table = "test_target"

    def __init__(
        self,
        db: SQLiteAdapter,
        job_name: str,
        execution_log: list[str],
    ) -> None:
        super().__init__(db=db)
        self.job_name = job_name
        self.execution_log = execution_log

    def execute_transform(
        self,
        run_id: int,
        window_start: str | None,
        window_end: str | None,
    ) -> TransformResult:
        self.execution_log.append(f"transform:{self.job_name}")
        return TransformResult(rows_read=1, rows_inserted=1)


class FailingTransformJob(BaseTransformJob):
    target_table = "test_target"

    def __init__(self, db: SQLiteAdapter, job_name: str, error_message: str) -> None:
        super().__init__(db=db)
        self.job_name = job_name
        self.error_message = error_message

    def execute_transform(
        self,
        run_id: int,
        window_start: str | None,
        window_end: str | None,
    ) -> TransformResult:
        raise RuntimeError(self.error_message)


def open_tracking_db(tmp_path: Path) -> SQLiteAdapter:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()
    create_tracking_tables(db)
    return db


def test_successful_full_pipeline_executes_all_phases_in_order(tmp_path: Path) -> None:
    db = open_tracking_db(tmp_path)

    try:
        execution_log: list[str] = []
        runner = FullPipelineRunner(db)

        run_id = runner.run_full_pipeline(
            direct_jobs=[
                RecordingExtractionJob(db, "direct_one", "direct", execution_log),
                RecordingExtractionJob(db, "direct_two", "direct", execution_log),
            ],
            staging_jobs=[
                RecordingExtractionJob(db, "staging_one", "staging", execution_log),
            ],
            transform_jobs=[
                RecordingTransformJob(db, "transform_one", execution_log),
            ],
            run_type="daily",
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
            notes="full pipeline test",
        )

        run_row = db.query_one("SELECT status, notes FROM extraction_run WHERE run_id = ?", [run_id])
        job_rows = db.query_all(
            "SELECT job_name, status FROM extraction_job_run ORDER BY job_run_id"
        )

        assert run_row is not None
        assert run_row["status"] == "completed"
        assert run_row["notes"] == "full pipeline test"
        assert execution_log == [
            "direct:direct_one",
            "direct:direct_two",
            "staging:staging_one",
            "transform:transform_one",
        ]
        assert job_rows == [
            {"job_name": "direct_one", "status": "completed"},
            {"job_name": "direct_two", "status": "completed"},
            {"job_name": "staging_one", "status": "completed"},
            {"job_name": "transform_one", "status": "completed"},
        ]
    finally:
        db.close()


@pytest.mark.parametrize(
    ("direct_jobs", "staging_jobs", "transform_jobs", "expected_error"),
    [
        (
            [("direct_failure", "direct failed")],
            [],
            [],
            "direct failed",
        ),
        (
            [],
            [("staging_failure", "staging failed")],
            [],
            "staging failed",
        ),
        (
            [],
            [],
            [("transform_failure", "transform failed")],
            "transform failed",
        ),
    ],
)
def test_failed_full_pipeline_marks_run_failed_and_logs_error(
    tmp_path: Path,
    direct_jobs: list[tuple[str, str]],
    staging_jobs: list[tuple[str, str]],
    transform_jobs: list[tuple[str, str]],
    expected_error: str,
) -> None:
    db = open_tracking_db(tmp_path)

    try:
        runner = FullPipelineRunner(db)

        with pytest.raises(RuntimeError, match=expected_error):
            runner.run_full_pipeline(
                direct_jobs=[
                    FailingExtractionJob(db, job_name, error)
                    for job_name, error in direct_jobs
                ],
                staging_jobs=[
                    FailingExtractionJob(db, job_name, error)
                    for job_name, error in staging_jobs
                ],
                transform_jobs=[
                    FailingTransformJob(db, job_name, error)
                    for job_name, error in transform_jobs
                ],
                run_type="daily",
                window_start="2026-05-25T00:00:00+02:00",
                window_end="2026-05-26T00:00:00+02:00",
            )

        run_row = db.query_one("SELECT run_id, status, notes FROM extraction_run")
        assert run_row is not None
        assert run_row["status"] == "failed"
        assert run_row["notes"] == expected_error

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
            "error_message": expected_error,
        }
    finally:
        db.close()

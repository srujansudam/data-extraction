from pathlib import Path

from data_extraction.db.schema import create_tracking_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.tracking.errors import ExtractionErrorLogger
from data_extraction.tracking.jobs import ExtractionJobTracker
from data_extraction.tracking.runs import ExtractionRunTracker


def test_log_error_creates_error_log_row(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)

        run_tracker = ExtractionRunTracker(db)
        run_id = run_tracker.start_run(
            run_type="daily",
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
            triggered_by="manual",
        )

        job_tracker = ExtractionJobTracker(db)
        job_run_id = job_tracker.start_job(
            run_id=run_id,
            job_name="office_accounts",
            source_system="flexcube",
            target_table="office_accounts",
            window_start=None,
            window_end=None,
        )

        error_logger = ExtractionErrorLogger(db)
        error_id = error_logger.log_error(
            run_id=run_id,
            job_run_id=job_run_id,
            job_name="office_accounts",
            source_system="flexcube",
            error_type="SourceQueryError",
            error_message="Test source query failed",
            error_detail="ORA test error detail",
        )

        row = db.query_one(
            """
            SELECT error_id, run_id, job_run_id, job_name, source_system,
                   error_type, error_message, error_detail
            FROM extraction_error_log
            WHERE error_id = ?
            """,
            [error_id],
        )

        assert row is not None
        assert row["error_id"] == 1
        assert row["run_id"] == run_id
        assert row["job_run_id"] == job_run_id
        assert row["job_name"] == "office_accounts"
        assert row["source_system"] == "flexcube"
        assert row["error_type"] == "SourceQueryError"
        assert row["error_message"] == "Test source query failed"
        assert row["error_detail"] == "ORA test error detail"
    finally:
        db.close()


def test_log_error_can_create_run_level_error_without_job(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)

        run_tracker = ExtractionRunTracker(db)
        run_id = run_tracker.start_run(
            run_type="daily",
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
            triggered_by="manual",
        )

        error_logger = ExtractionErrorLogger(db)
        error_id = error_logger.log_error(
            run_id=run_id,
            error_type="RunError",
            error_message="Test run failed",
        )

        row = db.query_one(
            """
            SELECT error_id, run_id, job_run_id, error_type, error_message
            FROM extraction_error_log
            WHERE error_id = ?
            """,
            [error_id],
        )

        assert row is not None
        assert row["error_id"] == 1
        assert row["run_id"] == run_id
        assert row["job_run_id"] is None
        assert row["error_type"] == "RunError"
        assert row["error_message"] == "Test run failed"
    finally:
        db.close()
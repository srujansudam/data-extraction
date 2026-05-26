from pathlib import Path

from data_extraction.db.schema import create_tracking_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.tracking.jobs import ExtractionJobTracker
from data_extraction.tracking.runs import ExtractionRunTracker


def create_test_run(db: SQLiteAdapter) -> int:
    run_tracker = ExtractionRunTracker(db)
    return run_tracker.start_run(
        run_type="daily",
        window_start="2026-05-25T00:00:00+02:00",
        window_end="2026-05-26T00:00:00+02:00",
        triggered_by="manual",
    )


def test_start_job_creates_running_job_run(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)
        run_id = create_test_run(db)

        job_tracker = ExtractionJobTracker(db)
        job_run_id = job_tracker.start_job(
            run_id=run_id,
            job_name="office_accounts",
            source_system="flexcube",
            target_table="office_accounts",
            window_start=None,
            window_end=None,
        )

        row = db.query_one(
            """
            SELECT job_run_id, run_id, job_name, source_system, target_table, status
            FROM extraction_job_run
            WHERE job_run_id = ?
            """,
            [job_run_id],
        )

        assert row is not None
        assert row["job_run_id"] == 1
        assert row["run_id"] == run_id
        assert row["job_name"] == "office_accounts"
        assert row["source_system"] == "flexcube"
        assert row["target_table"] == "office_accounts"
        assert row["status"] == "running"
    finally:
        db.close()


def test_complete_job_marks_job_completed_and_records_counts(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)
        run_id = create_test_run(db)

        job_tracker = ExtractionJobTracker(db)
        job_run_id = job_tracker.start_job(
            run_id=run_id,
            job_name="office_accounts",
            source_system="flexcube",
            target_table="office_accounts",
            window_start=None,
            window_end=None,
        )

        job_tracker.complete_job(
            job_run_id=job_run_id,
            rows_extracted=10,
            rows_inserted=8,
            rows_updated=2,
            rows_rejected=0,
        )

        row = db.query_one(
            """
            SELECT status, rows_extracted, rows_inserted, rows_updated, rows_rejected,
                   completed_at, error_message
            FROM extraction_job_run
            WHERE job_run_id = ?
            """,
            [job_run_id],
        )

        assert row is not None
        assert row["status"] == "completed"
        assert row["rows_extracted"] == 10
        assert row["rows_inserted"] == 8
        assert row["rows_updated"] == 2
        assert row["rows_rejected"] == 0
        assert row["completed_at"] is not None
        assert row["error_message"] is None
    finally:
        db.close()


def test_fail_job_marks_job_failed(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)
        run_id = create_test_run(db)

        job_tracker = ExtractionJobTracker(db)
        job_run_id = job_tracker.start_job(
            run_id=run_id,
            job_name="office_accounts",
            source_system="flexcube",
            target_table="office_accounts",
            window_start=None,
            window_end=None,
        )

        job_tracker.fail_job(job_run_id=job_run_id, error_message="test job failure")

        row = db.query_one(
            """
            SELECT status, completed_at, error_message
            FROM extraction_job_run
            WHERE job_run_id = ?
            """,
            [job_run_id],
        )

        assert row is not None
        assert row["status"] == "failed"
        assert row["completed_at"] is not None
        assert row["error_message"] == "test job failure"
    finally:
        db.close()
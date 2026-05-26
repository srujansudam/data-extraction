from pathlib import Path

from data_extraction.db.schema import create_tracking_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.tracking.runs import ExtractionRunTracker


def test_start_run_creates_running_extraction_run(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)

        tracker = ExtractionRunTracker(db)
        run_id = tracker.start_run(
            run_type="daily",
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
            triggered_by="manual",
            notes="test daily run",
        )

        row = db.query_one(
            """
            SELECT run_id, run_type, status, window_start, window_end, triggered_by, notes
            FROM extraction_run
            WHERE run_id = ?
            """,
            [run_id],
        )

        assert row is not None
        assert row["run_id"] == 1
        assert row["run_type"] == "daily"
        assert row["status"] == "running"
        assert row["window_start"] == "2026-05-25T00:00:00+02:00"
        assert row["window_end"] == "2026-05-26T00:00:00+02:00"
        assert row["triggered_by"] == "manual"
        assert row["notes"] == "test daily run"
    finally:
        db.close()


def test_complete_run_marks_run_completed(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)

        tracker = ExtractionRunTracker(db)
        run_id = tracker.start_run(
            run_type="daily",
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        tracker.complete_run(run_id, notes="completed successfully")

        row = db.query_one(
            """
            SELECT status, completed_at, notes
            FROM extraction_run
            WHERE run_id = ?
            """,
            [run_id],
        )

        assert row is not None
        assert row["status"] == "completed"
        assert row["completed_at"] is not None
        assert row["notes"] == "completed successfully"
    finally:
        db.close()


def test_fail_run_marks_run_failed(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)

        tracker = ExtractionRunTracker(db)
        run_id = tracker.start_run(
            run_type="daily",
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        tracker.fail_run(run_id, error_message="test failure")

        row = db.query_one(
            """
            SELECT status, completed_at, notes
            FROM extraction_run
            WHERE run_id = ?
            """,
            [run_id],
        )

        assert row is not None
        assert row["status"] == "failed"
        assert row["completed_at"] is not None
        assert row["notes"] == "test failure"
    finally:
        db.close()
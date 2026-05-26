from pathlib import Path

from data_extraction.db.schema import create_tracking_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.tracking.runs import ExtractionRunTracker
from data_extraction.tracking.watermarks import ExtractionWatermarkTracker


def create_test_run(db: SQLiteAdapter) -> int:
    run_tracker = ExtractionRunTracker(db)
    return run_tracker.start_run(
        run_type="daily",
        window_start="2026-05-25T00:00:00+02:00",
        window_end="2026-05-26T00:00:00+02:00",
        triggered_by="manual",
    )


def test_get_watermark_returns_none_when_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)

        tracker = ExtractionWatermarkTracker(db)

        assert tracker.get_watermark("office_accounts") is None
    finally:
        db.close()


def test_upsert_watermark_creates_watermark(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)
        run_id = create_test_run(db)

        tracker = ExtractionWatermarkTracker(db)
        tracker.upsert_watermark(
            job_name="office_accounts",
            source_system="flexcube",
            target_table="office_accounts",
            window_start=None,
            window_end=None,
            run_id=run_id,
        )

        row = tracker.get_watermark("office_accounts")

        assert row is not None
        assert row["job_name"] == "office_accounts"
        assert row["source_system"] == "flexcube"
        assert row["target_table"] == "office_accounts"
        assert row["last_successful_window_start"] is None
        assert row["last_successful_window_end"] is None
        assert row["last_successful_run_id"] == run_id
        assert row["updated_at"] is not None
    finally:
        db.close()


def test_upsert_watermark_updates_existing_watermark(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)
        run_id = create_test_run(db)

        tracker = ExtractionWatermarkTracker(db)

        tracker.upsert_watermark(
            job_name="transaction_data",
            source_system="orion",
            target_table="transaction_data",
            window_start="2026-05-24T00:00:00+02:00",
            window_end="2026-05-25T00:00:00+02:00",
            run_id=run_id,
        )

        tracker.upsert_watermark(
            job_name="transaction_data",
            source_system="orion",
            target_table="transaction_data",
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
            run_id=run_id,
        )

        row = tracker.get_watermark("transaction_data")

        assert row is not None
        assert row["job_name"] == "transaction_data"
        assert row["last_successful_window_start"] == "2026-05-25T00:00:00+02:00"
        assert row["last_successful_window_end"] == "2026-05-26T00:00:00+02:00"
    finally:
        db.close()
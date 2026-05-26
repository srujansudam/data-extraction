from pathlib import Path

from data_extraction.db.schema import create_tracking_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter


def test_create_tracking_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)

        rows = db.query_all(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        )

        table_names = {row["name"] for row in rows}

        assert "extraction_run" in table_names
        assert "extraction_job_run" in table_names
        assert "extraction_job_watermark" in table_names
        assert "extraction_error_log" in table_names
        assert "source_file_ingestion" in table_names
        assert "data_quality_check" in table_names
    finally:
        db.close()


def test_can_insert_extraction_run(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)

        db.execute(
            """
            INSERT INTO extraction_run (
                run_type,
                status,
                window_start,
                window_end,
                triggered_by,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                "daily",
                "running",
                "2026-05-25T00:00:00+02:00",
                "2026-05-26T00:00:00+02:00",
                "manual",
                "test run",
            ],
        )
        db.commit()

        row = db.query_one("SELECT run_type, status FROM extraction_run WHERE run_id = ?", [1])

        assert row == {"run_type": "daily", "status": "running"}
    finally:
        db.close()
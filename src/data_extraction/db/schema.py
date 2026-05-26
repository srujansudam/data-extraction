from __future__ import annotations

from data_extraction.db.adapter import DatabaseAdapter


TRACKING_TABLE_SQL = [
    """
    CREATE TABLE IF NOT EXISTS extraction_run (
        run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_type TEXT NOT NULL,
        status TEXT NOT NULL,
        window_start TEXT,
        window_end TEXT,
        started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        triggered_by TEXT NOT NULL DEFAULT 'scheduler',
        notes TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS extraction_job_run (
        job_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL,
        job_name TEXT NOT NULL,
        source_system TEXT NOT NULL,
        target_table TEXT NOT NULL,
        status TEXT NOT NULL,
        window_start TEXT,
        window_end TEXT,
        rows_extracted INTEGER NOT NULL DEFAULT 0,
        rows_inserted INTEGER NOT NULL DEFAULT 0,
        rows_updated INTEGER NOT NULL DEFAULT 0,
        rows_rejected INTEGER NOT NULL DEFAULT 0,
        started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        error_message TEXT,
        FOREIGN KEY (run_id) REFERENCES extraction_run(run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS extraction_job_watermark (
        job_name TEXT PRIMARY KEY,
        source_system TEXT NOT NULL,
        target_table TEXT NOT NULL,
        last_successful_window_start TEXT,
        last_successful_window_end TEXT,
        last_successful_run_id INTEGER,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS extraction_error_log (
        error_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        job_run_id INTEGER,
        job_name TEXT,
        source_system TEXT,
        error_type TEXT NOT NULL,
        error_message TEXT NOT NULL,
        error_detail TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (run_id) REFERENCES extraction_run(run_id),
        FOREIGN KEY (job_run_id) REFERENCES extraction_job_run(job_run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS source_file_ingestion (
        file_ingestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        source_system TEXT NOT NULL,
        source_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_hash TEXT,
        status TEXT NOT NULL,
        rows_read INTEGER NOT NULL DEFAULT 0,
        rows_loaded INTEGER NOT NULL DEFAULT 0,
        ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        error_message TEXT,
        FOREIGN KEY (run_id) REFERENCES extraction_run(run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS data_quality_check (
        check_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        job_run_id INTEGER,
        table_name TEXT NOT NULL,
        check_name TEXT NOT NULL,
        check_status TEXT NOT NULL,
        expected_value TEXT,
        actual_value TEXT,
        details TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (run_id) REFERENCES extraction_run(run_id),
        FOREIGN KEY (job_run_id) REFERENCES extraction_job_run(job_run_id)
    )
    """,
]


def create_tracking_tables(db: DatabaseAdapter) -> None:
    for sql in TRACKING_TABLE_SQL:
        db.execute(sql)

    db.commit()
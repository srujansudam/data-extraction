from __future__ import annotations

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.tracking.runs import current_timestamp


class ExtractionJobTracker:
    def __init__(self, db: DatabaseAdapter, timezone: str = "Europe/Malta") -> None:
        self.db = db
        self.timezone = timezone

    def start_job(
        self,
        run_id: int,
        job_name: str,
        source_system: str,
        target_table: str,
        window_start: str | None,
        window_end: str | None,
    ) -> int:
        job_run_id = self.db.execute_and_get_lastrow_id(
            """
            INSERT INTO extraction_job_run (
                run_id,
                job_name,
                source_system,
                target_table,
                status,
                window_start,
                window_end,
                started_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                job_name,
                source_system,
                target_table,
                "running",
                window_start,
                window_end,
                current_timestamp(self.timezone),
            ],
        )
        self.db.commit()
        return job_run_id

    def complete_job(
        self,
        job_run_id: int,
        rows_extracted: int = 0,
        rows_inserted: int = 0,
        rows_updated: int = 0,
        rows_rejected: int = 0,
    ) -> None:
        self.db.execute(
            """
            UPDATE extraction_job_run
            SET status = ?,
                rows_extracted = ?,
                rows_inserted = ?,
                rows_updated = ?,
                rows_rejected = ?,
                completed_at = ?,
                error_message = NULL
            WHERE job_run_id = ?
            """,
            [
                "completed",
                rows_extracted,
                rows_inserted,
                rows_updated,
                rows_rejected,
                current_timestamp(self.timezone),
                job_run_id,
            ],
        )
        self.db.commit()

    def fail_job(self, job_run_id: int, error_message: str) -> None:
        self.db.execute(
            """
            UPDATE extraction_job_run
            SET status = ?,
                completed_at = ?,
                error_message = ?
            WHERE job_run_id = ?
            """,
            [
                "failed",
                current_timestamp(self.timezone),
                error_message,
                job_run_id,
            ],
        )
        self.db.commit()
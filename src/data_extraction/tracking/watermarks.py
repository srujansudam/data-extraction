from __future__ import annotations

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.tracking.runs import current_timestamp


class ExtractionWatermarkTracker:
    def __init__(self, db: DatabaseAdapter, timezone: str = "Europe/Malta") -> None:
        self.db = db
        self.timezone = timezone

    def get_watermark(self, job_name: str) -> dict[str, object] | None:
        return self.db.query_one(
            """
            SELECT
                job_name,
                source_system,
                target_table,
                last_successful_window_start,
                last_successful_window_end,
                last_successful_run_id,
                updated_at
            FROM extraction_job_watermark
            WHERE job_name = ?
            """,
            [job_name],
        )

    def upsert_watermark(
        self,
        job_name: str,
        source_system: str,
        target_table: str,
        window_start: str | None,
        window_end: str | None,
        run_id: int,
    ) -> None:
        self.db.execute(
            """
            INSERT INTO extraction_job_watermark (
                job_name,
                source_system,
                target_table,
                last_successful_window_start,
                last_successful_window_end,
                last_successful_run_id,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_name) DO UPDATE SET
                source_system = excluded.source_system,
                target_table = excluded.target_table,
                last_successful_window_start = excluded.last_successful_window_start,
                last_successful_window_end = excluded.last_successful_window_end,
                last_successful_run_id = excluded.last_successful_run_id,
                updated_at = excluded.updated_at
            """,
            [
                job_name,
                source_system,
                target_table,
                window_start,
                window_end,
                run_id,
                current_timestamp(self.timezone),
            ],
        )
        self.db.commit()
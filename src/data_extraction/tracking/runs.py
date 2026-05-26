from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from data_extraction.db.adapter import DatabaseAdapter


def current_timestamp(timezone: str = "Europe/Malta") -> str:
    return datetime.now(ZoneInfo(timezone)).isoformat(timespec="seconds")


class ExtractionRunTracker:
    def __init__(self, db: DatabaseAdapter, timezone: str = "Europe/Malta") -> None:
        self.db = db
        self.timezone = timezone

    def start_run(
        self,
        run_type: str,
        window_start: str | None,
        window_end: str | None,
        triggered_by: str = "manual",
        notes: str | None = None,
    ) -> int:
        run_id = self.db.execute_and_get_lastrow_id(
            """
            INSERT INTO extraction_run (
                run_type,
                status,
                window_start,
                window_end,
                started_at,
                triggered_by,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_type,
                "running",
                window_start,
                window_end,
                current_timestamp(self.timezone),
                triggered_by,
                notes,
            ],
        )
        self.db.commit()
        return run_id

    def complete_run(self, run_id: int, notes: str | None = None) -> None:
        self.db.execute(
            """
            UPDATE extraction_run
            SET status = ?,
                completed_at = ?,
                notes = COALESCE(?, notes)
            WHERE run_id = ?
            """,
            [
                "completed",
                current_timestamp(self.timezone),
                notes,
                run_id,
            ],
        )
        self.db.commit()

    def fail_run(self, run_id: int, error_message: str) -> None:
        self.db.execute(
            """
            UPDATE extraction_run
            SET status = ?,
                completed_at = ?,
                notes = ?
            WHERE run_id = ?
            """,
            [
                "failed",
                current_timestamp(self.timezone),
                error_message,
                run_id,
            ],
        )
        self.db.commit()
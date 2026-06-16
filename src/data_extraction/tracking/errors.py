from __future__ import annotations

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.utils.redaction import redact_secret_values


class ExtractionErrorLogger:
    def __init__(self, db: DatabaseAdapter) -> None:
        self.db = db

    def log_error(
        self,
        error_type: str,
        error_message: str,
        run_id: int | None = None,
        job_run_id: int | None = None,
        job_name: str | None = None,
        source_system: str | None = None,
        error_detail: str | None = None,
    ) -> int:
        error_id = self.db.execute_and_get_lastrow_id(
            """
            INSERT INTO extraction_error_log (
                run_id,
                job_run_id,
                job_name,
                source_system,
                error_type,
                error_message,
                error_detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                job_run_id,
                job_name,
                source_system,
                error_type,
                redact_secret_values(error_message),
                redact_secret_values(error_detail) if error_detail is not None else None,
            ],
        )
        self.db.commit()
        return error_id

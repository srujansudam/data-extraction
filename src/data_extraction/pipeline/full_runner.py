from __future__ import annotations

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob
from data_extraction.tracking.errors import ExtractionErrorLogger
from data_extraction.tracking.runs import ExtractionRunTracker
from data_extraction.transform.base import BaseTransformJob
from data_extraction.utils.redaction import sanitize_exception


class FullPipelineRunner:
    def __init__(self, db: DatabaseAdapter, timezone: str = "Europe/Malta") -> None:
        self.db = db
        self.timezone = timezone
        self.run_tracker = ExtractionRunTracker(db, timezone)
        self.error_logger = ExtractionErrorLogger(db)

    def run_full_pipeline(
        self,
        direct_jobs: list[BaseExtractionJob],
        staging_jobs: list[BaseExtractionJob],
        transform_jobs: list[BaseTransformJob],
        run_type: str,
        window_start: str | None,
        window_end: str | None,
        triggered_by: str = "manual",
        notes: str | None = None,
    ) -> int:
        run_id = self.run_tracker.start_run(
            run_type=run_type,
            window_start=window_start,
            window_end=window_end,
            triggered_by=triggered_by,
            notes=notes,
        )

        try:
            for job in direct_jobs:
                job.run(run_id=run_id, window_start=window_start, window_end=window_end)

            for job in staging_jobs:
                job.run(run_id=run_id, window_start=window_start, window_end=window_end)

            for job in transform_jobs:
                job.run(run_id=run_id, window_start=window_start, window_end=window_end)

            self.run_tracker.complete_run(run_id)
            return run_id

        except Exception as exc:
            error_message = sanitize_exception(exc)
            self.run_tracker.fail_run(run_id, error_message)
            self.error_logger.log_error(
                run_id=run_id,
                error_type=exc.__class__.__name__,
                error_message=error_message,
                error_detail="Full pipeline run failed.",
            )
            raise

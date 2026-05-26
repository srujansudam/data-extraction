from __future__ import annotations

import logging
from dataclasses import dataclass

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult
from data_extraction.tracking.errors import ExtractionErrorLogger
from data_extraction.tracking.runs import ExtractionRunTracker

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractionRunResult:
    run_id: int
    job_results: dict[str, JobResult]


class ExtractionRunner:
    def __init__(self, db: DatabaseAdapter, timezone: str = "Europe/Malta") -> None:
        self.db = db
        self.timezone = timezone
        self.run_tracker = ExtractionRunTracker(db, timezone)
        self.error_logger = ExtractionErrorLogger(db)

    def run_jobs(
        self,
        run_type: str,
        jobs: list[BaseExtractionJob],
        window_start: str | None,
        window_end: str | None,
        triggered_by: str = "manual",
        notes: str | None = None,
    ) -> ExtractionRunResult:
        run_id = self.run_tracker.start_run(
            run_type=run_type,
            window_start=window_start,
            window_end=window_end,
            triggered_by=triggered_by,
            notes=notes,
        )

        logger.info("Started extraction run: run_id=%s run_type=%s", run_id, run_type)

        job_results: dict[str, JobResult] = {}

        try:
            for job in jobs:
                job_results[job.job_name] = job.run(
                    run_id=run_id,
                    window_start=window_start,
                    window_end=window_end,
                )

            self.run_tracker.complete_run(run_id, notes="Run completed successfully")
            logger.info("Completed extraction run: run_id=%s", run_id)

            return ExtractionRunResult(run_id=run_id, job_results=job_results)

        except Exception as exc:
            error_message = str(exc)
            self.run_tracker.fail_run(run_id, error_message=error_message)
            self.error_logger.log_error(
                run_id=run_id,
                error_type=exc.__class__.__name__,
                error_message=error_message,
            )
            logger.exception("Failed extraction run: run_id=%s", run_id)
            raise
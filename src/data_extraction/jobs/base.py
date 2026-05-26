from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.tracking.errors import ExtractionErrorLogger
from data_extraction.tracking.jobs import ExtractionJobTracker
from data_extraction.tracking.watermarks import ExtractionWatermarkTracker

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobResult:
    rows_extracted: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_rejected: int = 0


class BaseExtractionJob(ABC):
    job_name: str
    source_system: str
    target_table: str

    def __init__(self, db: DatabaseAdapter, timezone: str = "Europe/Malta") -> None:
        self.db = db
        self.timezone = timezone
        self.job_tracker = ExtractionJobTracker(db, timezone)
        self.error_logger = ExtractionErrorLogger(db)
        self.watermark_tracker = ExtractionWatermarkTracker(db, timezone)

    def run(
        self,
        run_id: int,
        window_start: str | None,
        window_end: str | None,
    ) -> JobResult:
        logger.info("Starting job: %s", self.job_name)

        job_run_id = self.job_tracker.start_job(
            run_id=run_id,
            job_name=self.job_name,
            source_system=self.source_system,
            target_table=self.target_table,
            window_start=window_start,
            window_end=window_end,
        )

        try:
            result = self.execute(window_start=window_start, window_end=window_end)

            self.job_tracker.complete_job(
                job_run_id=job_run_id,
                rows_extracted=result.rows_extracted,
                rows_inserted=result.rows_inserted,
                rows_updated=result.rows_updated,
                rows_rejected=result.rows_rejected,
            )

            self.watermark_tracker.upsert_watermark(
                job_name=self.job_name,
                source_system=self.source_system,
                target_table=self.target_table,
                window_start=window_start,
                window_end=window_end,
                run_id=run_id,
            )

            logger.info(
                "Completed job: %s | extracted=%s inserted=%s updated=%s rejected=%s",
                self.job_name,
                result.rows_extracted,
                result.rows_inserted,
                result.rows_updated,
                result.rows_rejected,
            )

            return result

        except Exception as exc:
            error_message = str(exc)

            self.job_tracker.fail_job(job_run_id=job_run_id, error_message=error_message)
            self.error_logger.log_error(
                run_id=run_id,
                job_run_id=job_run_id,
                job_name=self.job_name,
                source_system=self.source_system,
                error_type=exc.__class__.__name__,
                error_message=error_message,
            )

            logger.exception("Failed job: %s", self.job_name)
            raise

    @abstractmethod
    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        """
        Run the actual extraction and load logic.

        Concrete jobs will implement this method.
        """
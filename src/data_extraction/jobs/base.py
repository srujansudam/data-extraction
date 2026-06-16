from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.tracking.errors import ExtractionErrorLogger
from data_extraction.tracking.jobs import ExtractionJobTracker
from data_extraction.tracking.watermarks import ExtractionWatermarkTracker
from data_extraction.utils.redaction import sanitize_exception

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
        start_time = time.perf_counter()
        logger.info(
            "Job started | run_id=%s job_name=%s source_system=%s target_table=%s "
            "window_start=%s window_end=%s",
            run_id,
            self.job_name,
            self.source_system,
            self.target_table,
            window_start,
            window_end,
        )

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
                "Job completed | status=success run_id=%s job_name=%s source_system=%s "
                "target_table=%s duration_seconds=%.3f rows_extracted=%s rows_inserted=%s "
                "rows_updated=%s rows_rejected=%s",
                run_id,
                self.job_name,
                self.source_system,
                self.target_table,
                time.perf_counter() - start_time,
                result.rows_extracted,
                result.rows_inserted,
                result.rows_updated,
                result.rows_rejected,
            )

            return result

        except Exception as exc:
            error_message = sanitize_exception(exc)

            self.job_tracker.fail_job(job_run_id=job_run_id, error_message=error_message)
            self.error_logger.log_error(
                run_id=run_id,
                job_run_id=job_run_id,
                job_name=self.job_name,
                source_system=self.source_system,
                error_type=exc.__class__.__name__,
                error_message=error_message,
            )

            logger.error(
                "Job failed | status=failure run_id=%s job_name=%s source_system=%s "
                "target_table=%s duration_seconds=%.3f error_type=%s error_message=%s",
                run_id,
                self.job_name,
                self.source_system,
                self.target_table,
                time.perf_counter() - start_time,
                exc.__class__.__name__,
                error_message,
            )
            raise

    @abstractmethod
    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        """
        Run the actual extraction and load logic.

        Concrete jobs will implement this method.
        """

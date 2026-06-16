from __future__ import annotations

import logging

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult
from data_extraction.staging.writer import StagingWriter

logger = logging.getLogger(__name__)


class OracleToStagingJob(BaseExtractionJob):
    def __init__(
        self,
        db: DatabaseAdapter,
        source_client: SourceQueryClient,
        staging_writer: StagingWriter,
        job_name: str,
        source_system: str,
        source_object: str,
        staging_table: str,
        sql: str,
        requires_window: bool = False,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(db=db, timezone=timezone)
        self.source_client = source_client
        self.staging_writer = staging_writer
        self.job_name = job_name
        self.source_system = source_system
        self.source_object = source_object
        self.staging_table = staging_table
        self.target_table = staging_table
        self.sql = sql
        self.requires_window = requires_window

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        logger.info(
            "Source query started | job_name=%s source_system=%s source_object=%s "
            "target_table=%s requires_window=%s window_start=%s window_end=%s",
            self.job_name,
            self.source_system,
            self.source_object,
            self.staging_table,
            self.requires_window,
            window_start,
            window_end,
        )
        if self.requires_window:
            if window_start is None or window_end is None:
                raise ValueError(f"{self.job_name} requires window_start and window_end.")

            rows = self.source_client.query_all(
                self.sql,
                [window_start[:10], window_end[:10]],
            )
        else:
            rows = self.source_client.query_all(self.sql)

        logger.info(
            "Source query completed | job_name=%s source_system=%s target_table=%s rows_fetched=%s",
            self.job_name,
            self.source_system,
            self.staging_table,
            len(rows),
        )
        rows_written = self.staging_writer.write_rows(
            staging_table=self.staging_table,
            run_id=self._current_run_id,
            source_system=self.source_system,
            source_object=self.source_object,
            rows=rows,
        )
        logger.info(
            "Staging write completed | job_name=%s staging_table=%s rows_written=%s",
            self.job_name,
            self.staging_table,
            rows_written,
        )

        return JobResult(
            rows_extracted=len(rows),
            rows_inserted=rows_written,
            rows_updated=0,
            rows_rejected=0,
        )

    def run(
        self,
        run_id: int,
        window_start: str | None,
        window_end: str | None,
    ) -> JobResult:
        self._current_run_id = run_id
        return super().run(run_id=run_id, window_start=window_start, window_end=window_end)

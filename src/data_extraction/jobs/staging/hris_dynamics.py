from __future__ import annotations

from data_extraction.config.settings import HrisDynamicsEndpointConfig
from data_extraction.connectors.hris_dynamics import HrisDynamicsClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult
from data_extraction.staging.writer import StagingWriter


class HrisDynamicsEndpointStagingJob(BaseExtractionJob):
    def __init__(
        self,
        db: DatabaseAdapter,
        source_client: HrisDynamicsClient,
        staging_writer: StagingWriter,
        endpoint_name: str,
        endpoint_config: HrisDynamicsEndpointConfig,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(db=db, timezone=timezone)
        self.source_client = source_client
        self.staging_writer = staging_writer
        self.endpoint_name = endpoint_name
        self.endpoint_config = endpoint_config
        self.job_name = f"{endpoint_name}_staging"
        self.source_system = "hris"
        self.target_table = endpoint_config.target_table

    def execute(
        self,
        window_start: str | None,
        window_end: str | None,
    ) -> JobResult:
        del window_start, window_end
        rows = self.source_client.fetch_endpoint(self.endpoint_name)
        rows_written = self.staging_writer.write_rows(
            staging_table=self.endpoint_config.target_table,
            run_id=self._current_run_id,
            source_system="hris",
            source_object=self.endpoint_name,
            rows=rows,
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

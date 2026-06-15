from __future__ import annotations

from data_extraction.connectors.lotus_corba import LotusCorbaConnector
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult
from data_extraction.staging.lotus_corba_loader import (
    LOTUS_CORBA_STAGING_TARGETS,
    read_corba_rows,
)
from data_extraction.staging.writer import StagingWriter

LOTUS_CORBA_JOB_DATASETS = {
    "lotus_bov_employees": "bov_employees",
    "lotus_legal_rulings": "legal_rulings",
    "lotus_garnishee_orders": "garnishee_orders",
    "lotus_poa_revocation": "poa_revocation",
    "lotus_discrepancies_management": "discrepancies_management",
}


class LotusCorbaStagingJob(BaseExtractionJob):
    source_system = "lotus_notes"

    def __init__(
        self,
        db: DatabaseAdapter,
        connector: LotusCorbaConnector,
        staging_writer: StagingWriter,
        job_name: str,
        dataset: str,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(db=db, timezone=timezone)
        self.connector = connector
        self.staging_writer = staging_writer
        self.job_name = f"{job_name}_corba_staging"
        self.dataset = dataset
        self.staging_table, self.source_object = LOTUS_CORBA_STAGING_TARGETS[dataset]
        self.target_table = self.staging_table

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        output_path = self.connector.extract_dataset(self.dataset)
        rows = read_corba_rows(output_path)
        inserted = self.staging_writer.write_rows(
            staging_table=self.staging_table,
            run_id=self._current_run_id,
            source_system=self.source_system,
            source_object=self.source_object,
            rows=rows,
        )
        return JobResult(
            rows_extracted=len(rows),
            rows_inserted=inserted,
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

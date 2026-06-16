from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult
from data_extraction.staging.writer import StagingWriter

logger = logging.getLogger(__name__)


class ExcelToStagingJob(BaseExtractionJob):
    def __init__(
        self,
        db: DatabaseAdapter,
        staging_writer: StagingWriter,
        job_name: str,
        source_system: str,
        source_object: str,
        staging_table: str,
        file_path: str,
        sheet_name: str | None = None,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(db=db, timezone=timezone)
        self.staging_writer = staging_writer
        self.job_name = job_name
        self.source_system = source_system
        self.source_object = source_object
        self.staging_table = staging_table
        self.target_table = staging_table
        self.file_path = file_path
        self.sheet_name = sheet_name

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        path = Path(self.file_path)
        logger.info(
            "Lotus Excel file expected | job_name=%s source_object=%s staging_table=%s file_path=%s",
            self.job_name,
            self.source_object,
            self.staging_table,
            path,
        )
        if not path.exists():
            logger.error(
                "Lotus Excel file missing | job_name=%s source_object=%s file_path=%s",
                self.job_name,
                self.source_object,
                path,
            )
            raise FileNotFoundError(self.file_path)

        logger.info(
            "Lotus Excel file found | job_name=%s source_object=%s file_path=%s",
            self.job_name,
            self.source_object,
            path,
        )
        sheet_name: str | int = 0 if self.sheet_name is None else self.sheet_name
        dataframe = pd.read_excel(path, sheet_name=sheet_name)
        rows = _dataframe_to_rows(dataframe)
        logger.info(
            "Lotus Excel rows loaded | job_name=%s source_object=%s rows_loaded=%s",
            self.job_name,
            self.source_object,
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
            "Lotus Excel staging write completed | job_name=%s staging_table=%s rows_written=%s "
            "rows_rejected=%s",
            self.job_name,
            self.staging_table,
            rows_written,
            0,
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


def _dataframe_to_rows(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    dataframe = dataframe.astype(object).where(pd.notna(dataframe), None)
    return list(dataframe.to_dict(orient="records"))

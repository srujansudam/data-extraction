from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.staging.lotus_excel import (
    LotusBovEmployeesExcelStagingJob,
    LotusDiscrepanciesManagementExcelStagingJob,
    LotusGarnisheeOrdersExcelStagingJob,
    LotusLegalRulingsExcelStagingJob,
    LotusPoaRevocationExcelStagingJob,
)
from data_extraction.staging.writer import StagingWriter
from data_extraction.tracking.runs import ExtractionRunTracker


def create_test_run(db: SQLiteAdapter) -> int:
    run_tracker = ExtractionRunTracker(db)
    return run_tracker.start_run(
        run_type="daily",
        window_start=None,
        window_end=None,
        triggered_by="manual",
    )


@pytest.mark.parametrize(
    ("job_class", "staging_table", "expected_source_object"),
    [
        (LotusBovEmployeesExcelStagingJob, "stg_lotus_bov_employees", "LN - BOV Employees"),
        (
            LotusLegalRulingsExcelStagingJob,
            "stg_lotus_legal_rulings",
            "LN - Succession & Legal rulings",
        ),
        (
            LotusGarnisheeOrdersExcelStagingJob,
            "stg_lotus_garnishee_orders",
            "LN - Garnishee Orders",
        ),
        (
            LotusPoaRevocationExcelStagingJob,
            "stg_lotus_poa_revocation",
            "LN - POA Revocation",
        ),
        (
            LotusDiscrepanciesManagementExcelStagingJob,
            "stg_lotus_discrepancies_management",
            "LN - Discrepancies Management",
        ),
    ],
)
def test_lotus_excel_staging_jobs_write_expected_staging_table(
    tmp_path: Path,
    job_class: type[
        LotusBovEmployeesExcelStagingJob
        | LotusLegalRulingsExcelStagingJob
        | LotusGarnisheeOrdersExcelStagingJob
        | LotusPoaRevocationExcelStagingJob
        | LotusDiscrepanciesManagementExcelStagingJob
    ],
    staging_table: str,
    expected_source_object: str,
) -> None:
    excel_path = tmp_path / f"{staging_table}.xlsx"
    pd.DataFrame([{"Reference": "R001", "Name": "Ada"}]).to_excel(excel_path, index=False)

    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        job = job_class(
            db=db,
            file_path=str(excel_path),
            staging_writer=StagingWriter(db),
        )

        result = job.run(run_id=run_id, window_start=None, window_end=None)

        rows = db.query_all(f"SELECT source_system, source_object, source_payload FROM {staging_table}")

        assert result.rows_extracted == 1
        assert result.rows_inserted == 1
        assert rows[0]["source_system"] == "lotus_notes"
        assert rows[0]["source_object"] == expected_source_object
        assert json.loads(rows[0]["source_payload"]) == {"Reference": "R001", "Name": "Ada"}
    finally:
        db.close()

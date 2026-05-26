from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.staging.excel_to_staging import ExcelToStagingJob
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


def create_job(db: SQLiteAdapter, file_path: Path) -> ExcelToStagingJob:
    return ExcelToStagingJob(
        db=db,
        staging_writer=StagingWriter(db),
        job_name="test_excel_staging",
        source_system="lotus_notes",
        source_object="LN - BOV Employees",
        staging_table="stg_lotus_bov_employees",
        file_path=str(file_path),
    )


def test_excel_to_staging_job_reads_xlsx_and_writes_payload(tmp_path: Path) -> None:
    excel_path = tmp_path / "lotus.xlsx"
    pd.DataFrame(
        [
            {"Employee ID": "E001", "Name": "Ada", "Blank": None},
            {"Employee ID": "E002", "Name": "Grace", "Blank": None},
        ]
    ).to_excel(excel_path, index=False)

    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        job = create_job(db, excel_path)

        result = job.run(run_id=run_id, window_start=None, window_end=None)

        rows = db.query_all(
            """
            SELECT source_system, source_object, source_payload
            FROM stg_lotus_bov_employees
            ORDER BY staging_id
            """
        )

        assert result.rows_extracted == 2
        assert result.rows_inserted == 2
        assert rows[0]["source_system"] == "lotus_notes"
        assert rows[0]["source_object"] == "LN - BOV Employees"
        assert json.loads(rows[0]["source_payload"]) == {
            "Employee ID": "E001",
            "Name": "Ada",
            "Blank": None,
        }
    finally:
        db.close()


def test_excel_to_staging_job_missing_file_raises(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    job = create_job(db, tmp_path / "missing.xlsx")

    with pytest.raises(FileNotFoundError):
        job.execute(window_start=None, window_end=None)


def test_excel_to_staging_job_empty_sheet_succeeds(tmp_path: Path) -> None:
    excel_path = tmp_path / "empty.xlsx"
    pd.DataFrame(columns=["Employee ID", "Name"]).to_excel(excel_path, index=False)

    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        job = create_job(db, excel_path)

        result = job.run(run_id=run_id, window_start=None, window_end=None)

        assert result.rows_extracted == 0
        assert result.rows_inserted == 0
        assert db.query_all("SELECT * FROM stg_lotus_bov_employees") == []
    finally:
        db.close()

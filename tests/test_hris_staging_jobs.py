from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.staging.hris import (
    HrisAppendix3CrmStagingJob,
    HrisPersonnelContactDetailStagingJob,
    HrisStaffIdentificationStagingJob,
)
from data_extraction.staging.writer import StagingWriter
from data_extraction.tracking.runs import ExtractionRunTracker


class FakeSourceClient:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.executed_sql: str | None = None
        self.executed_params: Iterable[Any] | None = None

    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.executed_sql = sql
        self.executed_params = params
        return self.rows


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
        (
            HrisStaffIdentificationStagingJob,
            "stg_hris_staff_identification",
            "Staff Identification",
        ),
        (
            HrisPersonnelContactDetailStagingJob,
            "stg_hris_personnel_contact_detail",
            "Personnel Contact Detail",
        ),
        (
            HrisAppendix3CrmStagingJob,
            "stg_hris_appendix_3_crm",
            "Appendix 3 (CRM)",
        ),
    ],
)
def test_hris_staging_jobs_write_expected_staging_table(
    tmp_path: Path,
    job_class: type[
        HrisStaffIdentificationStagingJob
        | HrisPersonnelContactDetailStagingJob
        | HrisAppendix3CrmStagingJob
    ],
    staging_table: str,
    expected_source_object: str,
) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        source_client = FakeSourceClient(rows=[{"personnel_number": "P001"}])
        job = job_class(
            db=db,
            source_client=source_client,
            staging_writer=StagingWriter(db),
        )

        result = job.run(run_id=run_id, window_start=None, window_end=None)

        rows = db.query_all(f"SELECT source_system, source_object, source_payload FROM {staging_table}")

        assert source_client.executed_params is None
        assert result.rows_extracted == 1
        assert result.rows_inserted == 1
        assert rows[0]["source_system"] == "hris"
        assert rows[0]["source_object"] == expected_source_object
        assert json.loads(rows[0]["source_payload"]) == {"personnel_number": "P001"}
    finally:
        db.close()

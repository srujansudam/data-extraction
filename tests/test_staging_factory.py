from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.staging.factory import (
    create_hris_staging_job,
    create_lotus_excel_staging_job,
)
from data_extraction.jobs.staging.hris import HrisStaffIdentificationStagingJob
from data_extraction.jobs.staging.lotus_excel import LotusBovEmployeesExcelStagingJob
from data_extraction.staging.writer import StagingWriter


class FakeSourceClient:
    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        return []


def test_create_hris_staging_job_returns_known_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    staging_writer = StagingWriter(db)

    job = create_hris_staging_job(
        job_name="hris_staff_identification",
        db=db,
        source_client=FakeSourceClient(),
        staging_writer=staging_writer,
        timezone="UTC",
    )

    assert isinstance(job, HrisStaffIdentificationStagingJob)
    assert job.timezone == "UTC"


def test_create_hris_staging_job_raises_for_unknown_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))

    with pytest.raises(ValueError, match="Unknown HRIS staging job"):
        create_hris_staging_job(
            job_name="missing",
            db=db,
            source_client=FakeSourceClient(),
            staging_writer=StagingWriter(db),
        )


def test_create_lotus_excel_staging_job_returns_known_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    staging_writer = StagingWriter(db)

    job = create_lotus_excel_staging_job(
        job_name="lotus_bov_employees",
        db=db,
        file_path=str(tmp_path / "employees.xlsx"),
        staging_writer=staging_writer,
        timezone="UTC",
    )

    assert isinstance(job, LotusBovEmployeesExcelStagingJob)
    assert job.timezone == "UTC"


def test_create_lotus_excel_staging_job_raises_for_unknown_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))

    with pytest.raises(ValueError, match="Unknown Lotus Excel staging job"):
        create_lotus_excel_staging_job(
            job_name="missing",
            db=db,
            file_path=str(tmp_path / "missing.xlsx"),
            staging_writer=StagingWriter(db),
        )

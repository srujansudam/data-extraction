from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.staging.factory import (
    create_flexcube_staging_job,
    create_orion_staging_job,
)
from data_extraction.jobs.staging.flexcube import FlexcubeUserDetailsStagingJob
from data_extraction.jobs.staging.orion import OrionAccountsStagingJob
from data_extraction.staging.writer import StagingWriter


class FakeSourceClient:
    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        return []


def test_create_orion_staging_job_returns_known_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))

    job = create_orion_staging_job(
        job_name="orion_accounts",
        db=db,
        source_client=FakeSourceClient(),
        staging_writer=StagingWriter(db),
        timezone="UTC",
    )

    assert isinstance(job, OrionAccountsStagingJob)
    assert job.timezone == "UTC"


def test_create_orion_staging_job_raises_for_unknown_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))

    with pytest.raises(ValueError, match="Unknown ORION staging job"):
        create_orion_staging_job(
            job_name="missing",
            db=db,
            source_client=FakeSourceClient(),
            staging_writer=StagingWriter(db),
        )


def test_create_flexcube_staging_job_returns_known_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))

    job = create_flexcube_staging_job(
        job_name="flexcube_user_details",
        db=db,
        source_client=FakeSourceClient(),
        staging_writer=StagingWriter(db),
        timezone="UTC",
    )

    assert isinstance(job, FlexcubeUserDetailsStagingJob)
    assert job.timezone == "UTC"


def test_create_flexcube_staging_job_raises_for_unknown_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))

    with pytest.raises(ValueError, match="Unknown Flexcube staging job"):
        create_flexcube_staging_job(
            job_name="missing",
            db=db,
            source_client=FakeSourceClient(),
            staging_writer=StagingWriter(db),
        )

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.staging.oracle_to_staging import OracleToStagingJob
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
        window_start="2026-05-25T00:00:00+02:00",
        window_end="2026-05-26T00:00:00+02:00",
        triggered_by="manual",
    )


def create_job(
    db: SQLiteAdapter,
    source_client: FakeSourceClient,
    requires_window: bool = False,
) -> OracleToStagingJob:
    return OracleToStagingJob(
        db=db,
        source_client=source_client,
        staging_writer=StagingWriter(db),
        job_name="test_oracle_staging",
        source_system="hris",
        source_object="Staff Identification",
        staging_table="stg_hris_staff_identification",
        sql="SELECT 1 AS value FROM dual",
        requires_window=requires_window,
    )


def test_oracle_to_staging_job_queries_without_params_when_no_window_required(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        source_client = FakeSourceClient(rows=[{"personnel_number": "P001"}])
        job = create_job(db, source_client, requires_window=False)

        result = job.run(run_id=run_id, window_start=None, window_end=None)

        assert source_client.executed_sql == "SELECT 1 AS value FROM dual"
        assert source_client.executed_params is None
        assert result.rows_extracted == 1
        assert result.rows_inserted == 1
    finally:
        db.close()


def test_oracle_to_staging_job_uses_window_params_when_required(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        source_client = FakeSourceClient(rows=[{"personnel_number": "P001"}])
        job = create_job(db, source_client, requires_window=True)

        job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        assert source_client.executed_params == ["2026-05-25", "2026-05-26"]
    finally:
        db.close()


def test_oracle_to_staging_job_writes_json_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        source_client = FakeSourceClient(rows=[{"personnel_number": "P001", "name": "Ada"}])
        job = create_job(db, source_client)

        job.run(run_id=run_id, window_start=None, window_end=None)

        row = db.query_one(
            """
            SELECT run_id, source_system, source_object, source_payload
            FROM stg_hris_staff_identification
            """
        )

        assert row is not None
        assert row["run_id"] == run_id
        assert row["source_system"] == "hris"
        assert row["source_object"] == "Staff Identification"
        assert json.loads(row["source_payload"]) == {"personnel_number": "P001", "name": "Ada"}
    finally:
        db.close()


def test_oracle_to_staging_job_empty_rows_succeed(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        source_client = FakeSourceClient(rows=[])
        job = create_job(db, source_client)

        result = job.run(run_id=run_id, window_start=None, window_end=None)

        assert result.rows_extracted == 0
        assert result.rows_inserted == 0
        assert db.query_all("SELECT * FROM stg_hris_staff_identification") == []
    finally:
        db.close()


def test_oracle_to_staging_job_requires_window_when_configured(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    source_client = FakeSourceClient(rows=[])
    job = create_job(db, source_client, requires_window=True)

    with pytest.raises(ValueError, match="requires window_start and window_end"):
        job.execute(window_start=None, window_end="2026-05-26T00:00:00+02:00")

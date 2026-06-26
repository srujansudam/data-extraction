from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_extraction.config.settings import HrisDynamicsEndpointConfig
from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.staging.hris_dynamics import HrisDynamicsEndpointStagingJob
from data_extraction.staging.writer import StagingWriter
from data_extraction.tracking.runs import ExtractionRunTracker


class FakeHrisDynamicsClient:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.endpoint_names: list[str] = []

    def fetch_endpoint(self, endpoint_name: str) -> list[dict[str, Any]]:
        self.endpoint_names.append(endpoint_name)
        return self.rows


def test_hris_dynamics_endpoint_job_writes_configured_staging_table(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        run_id = ExtractionRunTracker(db).start_run(
            run_type="daily",
            window_start=None,
            window_end=None,
            triggered_by="manual",
        )
        source_client = FakeHrisDynamicsClient(
            [{"personnel_number": "P001", "_raw_record": {"employee_id": "P001"}}]
        )
        job = HrisDynamicsEndpointStagingJob(
            db=db,
            source_client=source_client,  # type: ignore[arg-type]
            staging_writer=StagingWriter(db),
            endpoint_name="hris_consolidated",
            endpoint_config=HrisDynamicsEndpointConfig(
                url="https://operations-bovd365.api.crm4.dynamics.com/api/data/v9.2/crfe9_hrisemployees",
                target_table="stg_hris_consolidated",
                columns={"worker_personnel_number": "crfe9_workerpersonnelnumber"},
            ),
        )

        result = job.run(run_id=run_id, window_start=None, window_end=None)

        rows = db.query_all(
            "SELECT source_system, source_object, source_payload "
            "FROM stg_hris_consolidated"
        )

        assert source_client.endpoint_names == ["hris_consolidated"]
        assert result.rows_extracted == 1
        assert result.rows_inserted == 1
        assert rows[0]["source_system"] == "hris"
        assert rows[0]["source_object"] == "hris_consolidated"
        assert json.loads(rows[0]["source_payload"]) == {
            "personnel_number": "P001",
            "_raw_record": {"employee_id": "P001"},
        }
    finally:
        db.close()

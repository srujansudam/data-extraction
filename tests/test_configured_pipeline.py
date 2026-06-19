from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.jobs.base import BaseExtractionJob
from data_extraction.transform.base import BaseTransformJob


class FakeSourceClient:
    def __init__(self) -> None:
        self.closed = False

    def query_all(self, sql: str, params=None) -> list[dict[str, Any]]:
        return []

    def close(self) -> None:
        self.closed = True


class FakePipelineJobBuilder:
    def __init__(
        self,
        db,
        source_clients: dict[str, SourceQueryClient],
        lotus_excel_file_paths: dict[str, str],
        hris_dynamics_endpoints=None,
        lotus_corba_connector=None,
        timezone: str = "Europe/Malta",
    ) -> None:
        self.db = db
        self.source_clients = source_clients
        self.lotus_excel_file_paths = lotus_excel_file_paths
        self.hris_dynamics_endpoints = hris_dynamics_endpoints
        self.lotus_corba_connector = lotus_corba_connector
        self.timezone = timezone

    def build_full_pipeline(
        self,
    ) -> tuple[list[BaseExtractionJob], list[BaseExtractionJob], list[BaseTransformJob]]:
        return [], [], []


class FakeFullPipelineRunner:
    last_call: dict[str, Any] | None = None

    def __init__(self, db, timezone: str = "Europe/Malta") -> None:
        self.db = db
        self.timezone = timezone

    def run_full_pipeline(
        self,
        direct_jobs: list[BaseExtractionJob],
        staging_jobs: list[BaseExtractionJob],
        transform_jobs: list[BaseTransformJob],
        run_type: str,
        window_start: str | None,
        window_end: str | None,
        triggered_by: str = "manual",
        notes: str | None = None,
    ) -> int:
        self.__class__.last_call = {
            "run_type": run_type,
            "window_start": window_start,
            "window_end": window_end,
            "triggered_by": triggered_by,
            "notes": notes,
        }
        return 99


def write_config(tmp_path: Path, lotus_files: dict[str, Path] | None = None) -> Path:
    lotus_file_lines = ""
    if lotus_files is not None:
        lotus_file_lines = "    files:\n" + "".join(
            f"      {job_name}: {path.as_posix()}\n" for job_name, path in lotus_files.items()
        )

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
app:
  name: data-extraction
  environment: test
database:
  type: sqlite
  path: {(tmp_path / "configured.db").as_posix()}
  encryption: none
sources:
  orion:
    type: oracle
    secret_ref: ORION_DB
    enabled: true
  flexcube:
    type: oracle
    secret_ref: FLEXCUBE_DB
    enabled: true
  hris:
    type: oracle
    secret_ref: HRIS_DB
    enabled: true
  lotus_notes:
    enabled: true
    mode: excel
    secret_ref: LOTUS_NOTES
    excel_input_folder: data/lotus_notes/incoming
{lotus_file_lines}extraction:
  daily_mode: previous_day
  backfill_years: 2
  timezone: Europe/Malta
logging:
  level: INFO
  folder: logs
""",
        encoding="utf-8",
    )
    return config_path


def required_lotus_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "lotus_bov_employees": tmp_path / "bov_employees.xlsx",
        "lotus_legal_rulings": tmp_path / "legal_rulings.xlsx",
        "lotus_garnishee_orders": tmp_path / "garnishee_orders.xlsx",
        "lotus_poa_revocation": tmp_path / "poa_revocation.xlsx",
        "lotus_discrepancies_management": tmp_path / "discrepancies_management.xlsx",
    }
    for path in files.values():
        path.write_text("placeholder", encoding="utf-8")
    return files


def patch_configured_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    source_clients: dict[str, FakeSourceClient] | None = None,
) -> dict[str, FakeSourceClient]:
    clients = source_clients or {
        "orion": FakeSourceClient(),
        "flexcube": FakeSourceClient(),
        "hris": FakeSourceClient(),
    }
    monkeypatch.setattr(
        "data_extraction.pipeline.configured_run.build_oracle_source_clients",
        lambda settings, secret_provider: clients,
    )
    monkeypatch.setattr(
        "data_extraction.pipeline.configured_run.PipelineJobBuilder",
        FakePipelineJobBuilder,
    )
    monkeypatch.setattr(
        "data_extraction.pipeline.configured_run.FullPipelineRunner",
        FakeFullPipelineRunner,
    )
    return clients


def test_configured_pipeline_rejects_unsupported_run_type(tmp_path: Path) -> None:
    from data_extraction.pipeline.configured_run import run_configured_pipeline

    config_path = write_config(tmp_path, required_lotus_files(tmp_path))

    with pytest.raises(ValueError, match="run_type must be one of"):
        run_configured_pipeline(str(config_path), run_type="weekly")


def test_configured_pipeline_validates_missing_lotus_excel_file_paths(tmp_path: Path) -> None:
    from data_extraction.pipeline.configured_run import run_configured_pipeline

    config_path = write_config(tmp_path, lotus_files=None)

    with pytest.raises(ValueError, match="Missing Lotus Excel file paths"):
        run_configured_pipeline(str(config_path), run_type="daily")


def test_configured_pipeline_runs_with_monkeypatched_source_clients(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from data_extraction.pipeline.configured_run import run_configured_pipeline

    clients = patch_configured_pipeline(monkeypatch)
    FakeFullPipelineRunner.last_call = None
    config_path = write_config(tmp_path, required_lotus_files(tmp_path))

    run_id = run_configured_pipeline(
        str(config_path),
        run_type="daily",
        triggered_by="test",
        reset_db=True,
    )

    assert run_id == 99
    assert FakeFullPipelineRunner.last_call is not None
    assert FakeFullPipelineRunner.last_call["run_type"] == "daily"
    assert FakeFullPipelineRunner.last_call["triggered_by"] == "test"
    assert FakeFullPipelineRunner.last_call["notes"] == "Configured daily pipeline"
    assert FakeFullPipelineRunner.last_call["window_start"] is not None
    assert FakeFullPipelineRunner.last_call["window_end"] is not None
    assert all(client.closed for client in clients.values())

    connection = sqlite3.connect(tmp_path / "configured.db")
    try:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        assert tables == []
    finally:
        connection.close()

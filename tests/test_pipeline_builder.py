from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from data_extraction.config.settings import HrisDynamics365Config, HrisDynamicsEndpointConfig
from data_extraction.connectors.hris_dynamics import HrisDynamicsClient
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.staging.hris_dynamics import HrisDynamicsEndpointStagingJob
from data_extraction.jobs.staging.lotus_corba import LotusCorbaStagingJob
from data_extraction.pipeline.builder import PipelineJobBuilder
from data_extraction.pipeline.definitions import (
    DIRECT_JOB_ORDER,
    STAGING_JOB_ORDER,
    TRANSFORM_JOB_ORDER,
)


class FakeSourceClient:
    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        return []


class FakeSecretProvider:
    def get_secret(self, secret_ref: str) -> dict[str, str]:
        return {"password": "secret"}


def lotus_file_paths() -> dict[str, str]:
    return {
        "lotus_bov_employees": "bov-employees.xlsx",
        "lotus_legal_rulings": "legal-rulings.xlsx",
        "lotus_garnishee_orders": "garnishee-orders.xlsx",
        "lotus_poa_revocation": "poa-revocation.xlsx",
        "lotus_discrepancies_management": "discrepancies.xlsx",
    }


def source_clients() -> dict[str, FakeSourceClient]:
    return {
        "orion": FakeSourceClient(),
        "flexcube": FakeSourceClient(),
        "hris": FakeSourceClient(),
    }


def hris_consolidated_endpoint() -> HrisDynamicsEndpointConfig:
    return HrisDynamicsEndpointConfig(
        url="https://operations-bovd365.api.crm4.dynamics.com/api/data/v9.2/crfe9_hrisemployees",
        target_table="stg_hris_consolidated",
        columns={"worker_personnel_number": "crfe9_workerpersonnelnumber"},
    )


def dynamics_source_clients() -> dict[str, FakeSourceClient | HrisDynamicsClient]:
    endpoint_config = hris_consolidated_endpoint()
    return {
        "orion": FakeSourceClient(),
        "flexcube": FakeSourceClient(),
        "hris": HrisDynamicsClient(
            HrisDynamics365Config(
                tenant_id="tenant",
                client_id="client",
                secret_ref="HRIS_D365_PROD",
                token_url="https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                scope="https://example.crm/.default",
                endpoints={"hris_consolidated": endpoint_config},
            ),
            FakeSecretProvider(),
        ),
    }


def create_builder(tmp_path: Path) -> PipelineJobBuilder:
    endpoint_config = hris_consolidated_endpoint()
    return PipelineJobBuilder(
        db=SQLiteAdapter(str(tmp_path / "test.db")),
        source_clients=dynamics_source_clients(),  # type: ignore[arg-type]
        lotus_excel_file_paths=lotus_file_paths(),
        hris_dynamics_endpoints={"hris_consolidated": endpoint_config},
    )


def test_build_direct_jobs_returns_jobs_in_direct_order(tmp_path: Path) -> None:
    builder = create_builder(tmp_path)

    jobs = builder.build_direct_jobs()

    assert [job.job_name for job in jobs] == DIRECT_JOB_ORDER


def test_build_staging_jobs_returns_jobs_in_staging_order(tmp_path: Path) -> None:
    builder = create_builder(tmp_path)

    jobs = builder.build_staging_jobs()

    assert [_staging_definition_name(job.job_name) for job in jobs] == STAGING_JOB_ORDER


def test_build_transform_jobs_returns_jobs_in_transform_order(tmp_path: Path) -> None:
    builder = create_builder(tmp_path)

    jobs = builder.build_transform_jobs()

    assert [job.job_name for job in jobs] == TRANSFORM_JOB_ORDER


def test_build_full_pipeline_returns_all_pipeline_phases(tmp_path: Path) -> None:
    builder = create_builder(tmp_path)

    direct_jobs, staging_jobs, transform_jobs = builder.build_full_pipeline()

    assert [job.job_name for job in direct_jobs] == DIRECT_JOB_ORDER
    assert [_staging_definition_name(job.job_name) for job in staging_jobs] == STAGING_JOB_ORDER
    assert [job.job_name for job in transform_jobs] == TRANSFORM_JOB_ORDER


def test_missing_source_client_raises_clear_value_error(tmp_path: Path) -> None:
    builder = PipelineJobBuilder(
        db=SQLiteAdapter(str(tmp_path / "test.db")),
        source_clients={"orion": FakeSourceClient(), "flexcube": FakeSourceClient()},
        lotus_excel_file_paths=lotus_file_paths(),
    )

    with pytest.raises(
        ValueError,
        match="Missing source client for 'hris' required by staging job 'hris_staff_identification'",
    ):
        builder.build_staging_jobs(["hris_staff_identification"])


def test_missing_lotus_file_path_raises_clear_value_error(tmp_path: Path) -> None:
    builder = PipelineJobBuilder(
        db=SQLiteAdapter(str(tmp_path / "test.db")),
        source_clients=source_clients(),
        lotus_excel_file_paths={"lotus_bov_employees": "bov-employees.xlsx"},
    )

    with pytest.raises(
        ValueError,
        match="Missing Lotus Excel file path for staging job 'lotus_legal_rulings'",
    ):
        builder.build_staging_jobs(["lotus_legal_rulings"])


def test_corba_connector_builds_corba_staging_jobs_without_excel_paths(
    tmp_path: Path,
) -> None:
    connector = object()
    builder = PipelineJobBuilder(
        db=SQLiteAdapter(str(tmp_path / "test.db")),
        source_clients=source_clients(),
        lotus_excel_file_paths={},
        lotus_corba_connector=connector,  # type: ignore[arg-type]
    )

    jobs = builder.build_staging_jobs(["lotus_bov_employees"])

    assert len(jobs) == 1
    assert isinstance(jobs[0], LotusCorbaStagingJob)
    assert jobs[0].dataset == "bov_employees"


def test_hris_dynamics_endpoint_config_builds_dynamics_staging_job(tmp_path: Path) -> None:
    endpoint_config = hris_consolidated_endpoint()
    hris_client = HrisDynamicsClient(
        HrisDynamics365Config(
            tenant_id="tenant",
            client_id="client",
            secret_ref="HRIS_D365_PROD",
            token_url="https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            scope="https://example.crm/.default",
            endpoints={"hris_consolidated": endpoint_config},
        ),
        FakeSecretProvider(),
    )
    builder = PipelineJobBuilder(
        db=SQLiteAdapter(str(tmp_path / "test.db")),
        source_clients={
            "orion": FakeSourceClient(),
            "flexcube": FakeSourceClient(),
            "hris": hris_client,
        },
        lotus_excel_file_paths=lotus_file_paths(),
        hris_dynamics_endpoints={"hris_consolidated": endpoint_config},
    )

    jobs = builder.build_staging_jobs(["hris_consolidated"])

    assert len(jobs) == 1
    assert isinstance(jobs[0], HrisDynamicsEndpointStagingJob)
    assert jobs[0].target_table == "stg_hris_consolidated"


def _staging_definition_name(job_name: str) -> str:
    return job_name.removesuffix("_excel_staging").removesuffix("_staging")

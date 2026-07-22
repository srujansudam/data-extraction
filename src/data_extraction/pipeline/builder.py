from __future__ import annotations

from data_extraction.config.settings import HrisDynamicsEndpointConfig
from data_extraction.connectors.base import SourceQueryClient
from data_extraction.connectors.hris_dynamics import HrisDynamicsClient
from data_extraction.connectors.lotus_corba import LotusCorbaConnector
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob
from data_extraction.jobs.factory import JOB_CLASSES, create_job
from data_extraction.jobs.staging.factory import (
    FLEXCUBE_STAGING_JOB_CLASSES,
    HRIS_STAGING_JOB_CLASSES,
    LOTUS_EXCEL_STAGING_JOB_CLASSES,
    ORION_STAGING_JOB_CLASSES,
    create_flexcube_staging_job,
    create_hris_staging_job,
    create_lotus_excel_staging_job,
    create_orion_staging_job,
)
from data_extraction.jobs.staging.hris_dynamics import HrisDynamicsEndpointStagingJob
from data_extraction.jobs.staging.lotus_corba import (
    LOTUS_CORBA_JOB_DATASETS,
    LotusCorbaStagingJob,
)
from data_extraction.pipeline.definitions import (
    DIRECT_JOB_ORDER,
    STAGING_JOB_ORDER,
    STAGING_JOB_SOURCES,
    TRANSFORM_JOB_ORDER,
)
from data_extraction.staging.writer import StagingWriter
from data_extraction.transform.base import BaseTransformJob
from data_extraction.transform.factory import create_transform_job


class PipelineJobBuilder:
    def __init__(
        self,
        db: DatabaseAdapter,
        source_clients: dict[str, SourceQueryClient],
        lotus_excel_file_paths: dict[str, str],
        hris_dynamics_endpoints: dict[str, HrisDynamicsEndpointConfig] | None = None,
        lotus_corba_connector: LotusCorbaConnector | None = None,
        enabled_sources: set[str] | None = None,
        timezone: str = "Europe/Malta",
    ) -> None:
        self.db = db
        self.source_clients = source_clients
        self.lotus_excel_file_paths = lotus_excel_file_paths
        self.hris_dynamics_endpoints = hris_dynamics_endpoints or {}
        self.lotus_corba_connector = lotus_corba_connector
        self.enabled_sources = enabled_sources
        self.timezone = timezone
        self.staging_writer = StagingWriter(db)

    def build_direct_jobs(self, job_names: list[str] | None = None) -> list[BaseExtractionJob]:
        selected_job_names = self._filter_direct_job_names(job_names or DIRECT_JOB_ORDER)
        return [
            create_job(
                job_name=job_name,
                db=self.db,
                source_clients=self.source_clients,
                timezone=self.timezone,
            )
            for job_name in selected_job_names
        ]

    def build_staging_jobs(self, job_names: list[str] | None = None) -> list[BaseExtractionJob]:
        selected_job_names = self._filter_staging_job_names(job_names or STAGING_JOB_ORDER)
        return [self._build_staging_job(job_name) for job_name in selected_job_names]

    def build_transform_jobs(self, job_names: list[str] | None = None) -> list[BaseTransformJob]:
        selected_job_names = job_names or TRANSFORM_JOB_ORDER
        return [
            create_transform_job(
                job_name=job_name,
                db=self.db,
                timezone=self.timezone,
            )
            for job_name in selected_job_names
        ]

    def build_full_pipeline(
        self,
    ) -> tuple[list[BaseExtractionJob], list[BaseExtractionJob], list[BaseTransformJob]]:
        return (
            self.build_direct_jobs(),
            self.build_staging_jobs(),
            self.build_transform_jobs(),
        )

    def _build_staging_job(self, job_name: str) -> BaseExtractionJob:
        if job_name in self.hris_dynamics_endpoints:
            return HrisDynamicsEndpointStagingJob(
                db=self.db,
                source_client=self._hris_dynamics_client(job_name),
                staging_writer=self.staging_writer,
                endpoint_name=job_name,
                endpoint_config=self._hris_dynamics_endpoint(job_name),
                timezone=self.timezone,
            )

        if job_name in ORION_STAGING_JOB_CLASSES:
            return create_orion_staging_job(
                job_name=job_name,
                db=self.db,
                source_client=self._source_client("orion", job_name),
                staging_writer=self.staging_writer,
                timezone=self.timezone,
            )

        if job_name in FLEXCUBE_STAGING_JOB_CLASSES:
            return create_flexcube_staging_job(
                job_name=job_name,
                db=self.db,
                source_client=self._source_client("flexcube", job_name),
                staging_writer=self.staging_writer,
                timezone=self.timezone,
            )

        if job_name in HRIS_STAGING_JOB_CLASSES:
            return create_hris_staging_job(
                job_name=job_name,
                db=self.db,
                source_client=self._source_client("hris", job_name),
                staging_writer=self.staging_writer,
                timezone=self.timezone,
            )

        if job_name in LOTUS_EXCEL_STAGING_JOB_CLASSES:
            if self.lotus_corba_connector is not None:
                return LotusCorbaStagingJob(
                    db=self.db,
                    connector=self.lotus_corba_connector,
                    staging_writer=self.staging_writer,
                    job_name=job_name,
                    dataset=LOTUS_CORBA_JOB_DATASETS[job_name],
                    timezone=self.timezone,
                )
            return create_lotus_excel_staging_job(
                job_name=job_name,
                db=self.db,
                file_path=self._lotus_file_path(job_name),
                staging_writer=self.staging_writer,
                timezone=self.timezone,
            )

        known_jobs = sorted(
            [
                *ORION_STAGING_JOB_CLASSES,
                *FLEXCUBE_STAGING_JOB_CLASSES,
                *HRIS_STAGING_JOB_CLASSES,
                *self.hris_dynamics_endpoints,
                *LOTUS_EXCEL_STAGING_JOB_CLASSES,
            ]
        )
        raise ValueError(
            f"Unknown staging job '{job_name}'. Available staging jobs: {', '.join(known_jobs)}"
        )

    def _source_client(self, source_system: str, job_name: str) -> SourceQueryClient:
        try:
            return self.source_clients[source_system]
        except KeyError as exc:
            available_clients = ", ".join(sorted(self.source_clients)) or "none"
            raise ValueError(
                f"Missing source client for '{source_system}' required by staging job "
                f"'{job_name}'. Available source clients: {available_clients}"
            ) from exc

    def _hris_dynamics_client(self, job_name: str) -> HrisDynamicsClient:
        source_client = self._source_client("hris", job_name)
        if not isinstance(source_client, HrisDynamicsClient) and not callable(
            getattr(source_client, "fetch_endpoint", None)
        ):
            raise ValueError(
                f"HRIS staging job '{job_name}' requires an HRIS Dynamics client when "
                "HRIS Dynamics endpoints are configured."
            )
        return source_client  # type: ignore[return-value]

    def _hris_dynamics_endpoint(self, job_name: str) -> HrisDynamicsEndpointConfig:
        try:
            return self.hris_dynamics_endpoints[job_name]
        except KeyError as exc:
            available_endpoints = ", ".join(sorted(self.hris_dynamics_endpoints)) or "none"
            raise ValueError(
                f"Missing HRIS Dynamics endpoint config for staging job '{job_name}'. "
                f"Available HRIS Dynamics endpoints: {available_endpoints}"
            ) from exc

    def _lotus_file_path(self, job_name: str) -> str:
        try:
            return self.lotus_excel_file_paths[job_name]
        except KeyError as exc:
            available_paths = ", ".join(sorted(self.lotus_excel_file_paths)) or "none"
            raise ValueError(
                f"Missing Lotus Excel file path for staging job '{job_name}'. "
                f"Available Lotus file paths: {available_paths}"
            ) from exc

    def _filter_direct_job_names(self, job_names: list[str]) -> list[str]:
        if self.enabled_sources is None:
            return job_names

        return [
            job_name
            for job_name in job_names
            if self._direct_job_source(job_name) in self.enabled_sources
        ]

    def _filter_staging_job_names(self, job_names: list[str]) -> list[str]:
        if self.enabled_sources is None:
            return job_names

        return [
            job_name
            for job_name in job_names
            if self._staging_job_source(job_name) in self.enabled_sources
        ]

    def _direct_job_source(self, job_name: str) -> str:
        try:
            return JOB_CLASSES[job_name].source_system
        except KeyError as exc:
            available_jobs = ", ".join(sorted(JOB_CLASSES))
            raise ValueError(f"Unknown job '{job_name}'. Available jobs: {available_jobs}") from exc

    def _staging_job_source(self, job_name: str) -> str:
        if job_name in STAGING_JOB_SOURCES:
            return STAGING_JOB_SOURCES[job_name]
        if job_name in self.hris_dynamics_endpoints:
            return "hris"
        known_jobs = sorted([*STAGING_JOB_SOURCES, *self.hris_dynamics_endpoints])
        raise ValueError(
            f"Unknown staging job '{job_name}'. Available staging jobs: {', '.join(known_jobs)}"
        )

from __future__ import annotations

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.staging.excel_to_staging import ExcelToStagingJob
from data_extraction.jobs.staging.hris import (
    HrisAppendix3CrmStagingJob,
    HrisPersonnelContactDetailStagingJob,
    HrisStaffIdentificationStagingJob,
)
from data_extraction.jobs.staging.lotus_excel import (
    LotusBovEmployeesExcelStagingJob,
    LotusDiscrepanciesManagementExcelStagingJob,
    LotusGarnisheeOrdersExcelStagingJob,
    LotusLegalRulingsExcelStagingJob,
    LotusPoaRevocationExcelStagingJob,
)
from data_extraction.jobs.staging.oracle_to_staging import OracleToStagingJob
from data_extraction.staging.writer import StagingWriter


HRIS_STAGING_JOB_CLASSES: dict[str, type[OracleToStagingJob]] = {
    "hris_staff_identification": HrisStaffIdentificationStagingJob,
    "hris_personnel_contact_detail": HrisPersonnelContactDetailStagingJob,
    "hris_appendix_3_crm": HrisAppendix3CrmStagingJob,
}

LOTUS_EXCEL_STAGING_JOB_CLASSES: dict[str, type[ExcelToStagingJob]] = {
    "lotus_bov_employees": LotusBovEmployeesExcelStagingJob,
    "lotus_legal_rulings": LotusLegalRulingsExcelStagingJob,
    "lotus_garnishee_orders": LotusGarnisheeOrdersExcelStagingJob,
    "lotus_poa_revocation": LotusPoaRevocationExcelStagingJob,
    "lotus_discrepancies_management": LotusDiscrepanciesManagementExcelStagingJob,
}


def create_hris_staging_job(
    job_name: str,
    db: DatabaseAdapter,
    source_client: SourceQueryClient,
    staging_writer: StagingWriter,
    timezone: str = "Europe/Malta",
) -> OracleToStagingJob:
    try:
        job_class = HRIS_STAGING_JOB_CLASSES[job_name]
    except KeyError as exc:
        available_jobs = ", ".join(sorted(HRIS_STAGING_JOB_CLASSES))
        raise ValueError(f"Unknown HRIS staging job '{job_name}'. Available jobs: {available_jobs}") from exc

    return job_class(
        db=db,
        source_client=source_client,
        staging_writer=staging_writer,
        timezone=timezone,
    )


def create_lotus_excel_staging_job(
    job_name: str,
    db: DatabaseAdapter,
    file_path: str,
    staging_writer: StagingWriter,
    timezone: str = "Europe/Malta",
) -> ExcelToStagingJob:
    try:
        job_class = LOTUS_EXCEL_STAGING_JOB_CLASSES[job_name]
    except KeyError as exc:
        available_jobs = ", ".join(sorted(LOTUS_EXCEL_STAGING_JOB_CLASSES))
        raise ValueError(
            f"Unknown Lotus Excel staging job '{job_name}'. Available jobs: {available_jobs}"
        ) from exc

    return job_class(
        db=db,
        file_path=file_path,
        staging_writer=staging_writer,
        timezone=timezone,
    )

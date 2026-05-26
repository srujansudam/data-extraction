from __future__ import annotations

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.staging.excel_to_staging import ExcelToStagingJob
from data_extraction.staging.writer import StagingWriter


class LotusBovEmployeesExcelStagingJob(ExcelToStagingJob):
    def __init__(
        self,
        db: DatabaseAdapter,
        file_path: str,
        staging_writer: StagingWriter,
        sheet_name: str | None = None,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(
            db=db,
            staging_writer=staging_writer,
            job_name="lotus_bov_employees_excel_staging",
            source_system="lotus_notes",
            source_object="LN - BOV Employees",
            staging_table="stg_lotus_bov_employees",
            file_path=file_path,
            sheet_name=sheet_name,
            timezone=timezone,
        )


class LotusLegalRulingsExcelStagingJob(ExcelToStagingJob):
    def __init__(
        self,
        db: DatabaseAdapter,
        file_path: str,
        staging_writer: StagingWriter,
        sheet_name: str | None = None,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(
            db=db,
            staging_writer=staging_writer,
            job_name="lotus_legal_rulings_excel_staging",
            source_system="lotus_notes",
            source_object="LN - Succession & Legal rulings",
            staging_table="stg_lotus_legal_rulings",
            file_path=file_path,
            sheet_name=sheet_name,
            timezone=timezone,
        )


class LotusGarnisheeOrdersExcelStagingJob(ExcelToStagingJob):
    def __init__(
        self,
        db: DatabaseAdapter,
        file_path: str,
        staging_writer: StagingWriter,
        sheet_name: str | None = None,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(
            db=db,
            staging_writer=staging_writer,
            job_name="lotus_garnishee_orders_excel_staging",
            source_system="lotus_notes",
            source_object="LN - Garnishee Orders",
            staging_table="stg_lotus_garnishee_orders",
            file_path=file_path,
            sheet_name=sheet_name,
            timezone=timezone,
        )


class LotusPoaRevocationExcelStagingJob(ExcelToStagingJob):
    def __init__(
        self,
        db: DatabaseAdapter,
        file_path: str,
        staging_writer: StagingWriter,
        sheet_name: str | None = None,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(
            db=db,
            staging_writer=staging_writer,
            job_name="lotus_poa_revocation_excel_staging",
            source_system="lotus_notes",
            source_object="LN - POA Revocation",
            staging_table="stg_lotus_poa_revocation",
            file_path=file_path,
            sheet_name=sheet_name,
            timezone=timezone,
        )


class LotusDiscrepanciesManagementExcelStagingJob(ExcelToStagingJob):
    def __init__(
        self,
        db: DatabaseAdapter,
        file_path: str,
        staging_writer: StagingWriter,
        sheet_name: str | None = None,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(
            db=db,
            staging_writer=staging_writer,
            job_name="lotus_discrepancies_management_excel_staging",
            source_system="lotus_notes",
            source_object="LN - Discrepancies Management",
            staging_table="stg_lotus_discrepancies_management",
            file_path=file_path,
            sheet_name=sheet_name,
            timezone=timezone,
        )

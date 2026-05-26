from __future__ import annotations

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.staging.oracle_to_staging import OracleToStagingJob
from data_extraction.staging.writer import StagingWriter


HRIS_STAFF_IDENTIFICATION_SQL = """
SELECT
    "Personnel Number" AS personnel_number,
    "Name" AS name,
    "Identification Number" AS identification_number,
    "Department" AS department,
    "Primary Position Description" AS primary_position_description,
    "Primary Position Category" AS primary_position_category
FROM "Staff Identification"
"""

HRIS_PERSONNEL_CONTACT_DETAIL_SQL = """
SELECT
    "Personnel Number" AS personnel_number,
    "National ID" AS national_id,
    "First Name" AS first_name,
    "Last Name" AS last_name,
    "Department Name" AS department_name,
    "Relationship Type" AS relationship_type,
    "Rel First Name" AS rel_first_name,
    "Rel Last Name" AS rel_last_name,
    "Rel National ID" AS rel_national_id,
    "Rel Gender" AS rel_gender
FROM "Personnel Contact Detail"
"""

HRIS_APPENDIX_3_CRM_SQL = """
SELECT
    "PersonnelNumber" AS personnel_number,
    "BOVNT_Custom" AS bovnt_custom,
    "IdentityEmail" AS identity_email,
    "ID Number" AS id_number,
    "Full Name" AS full_name,
    "EXCO Member" AS exco_member,
    "Department Name" AS department_name,
    "Section Name" AS section_name,
    "Sub-section" AS sub_section,
    "Branch Posted" AS branch_posted,
    "Main Department" AS main_department,
    "Main Section" AS main_section,
    "Main Sub-section" AS main_sub_section,
    "Primary Position" AS primary_position,
    "Primary Position Description" AS primary_position_description,
    "Primary Position Category" AS primary_position_category,
    "Manager Name" AS manager_name,
    "Manager Position" AS manager_position,
    "Manager Email" AS manager_email,
    "LastName" AS last_name,
    "FirstName" AS first_name
FROM "Appendix 3 (CRM)"
"""


class HrisStaffIdentificationStagingJob(OracleToStagingJob):
    def __init__(
        self,
        db: DatabaseAdapter,
        source_client: SourceQueryClient,
        staging_writer: StagingWriter,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(
            db=db,
            source_client=source_client,
            staging_writer=staging_writer,
            job_name="hris_staff_identification_staging",
            source_system="hris",
            source_object="Staff Identification",
            staging_table="stg_hris_staff_identification",
            sql=HRIS_STAFF_IDENTIFICATION_SQL,
            requires_window=False,
            timezone=timezone,
        )


class HrisPersonnelContactDetailStagingJob(OracleToStagingJob):
    def __init__(
        self,
        db: DatabaseAdapter,
        source_client: SourceQueryClient,
        staging_writer: StagingWriter,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(
            db=db,
            source_client=source_client,
            staging_writer=staging_writer,
            job_name="hris_personnel_contact_detail_staging",
            source_system="hris",
            source_object="Personnel Contact Detail",
            staging_table="stg_hris_personnel_contact_detail",
            sql=HRIS_PERSONNEL_CONTACT_DETAIL_SQL,
            requires_window=False,
            timezone=timezone,
        )


class HrisAppendix3CrmStagingJob(OracleToStagingJob):
    def __init__(
        self,
        db: DatabaseAdapter,
        source_client: SourceQueryClient,
        staging_writer: StagingWriter,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(
            db=db,
            source_client=source_client,
            staging_writer=staging_writer,
            job_name="hris_appendix_3_crm_staging",
            source_system="hris",
            source_object="Appendix 3 (CRM)",
            staging_table="stg_hris_appendix_3_crm",
            sql=HRIS_APPENDIX_3_CRM_SQL,
            requires_window=False,
            timezone=timezone,
        )

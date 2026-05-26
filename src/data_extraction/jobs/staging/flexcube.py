from __future__ import annotations

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.staging.oracle_to_staging import OracleToStagingJob
from data_extraction.staging.writer import StagingWriter


FLEXCUBE_DECEASED_CUSTOMERS_SQL = """
SELECT
    customer_no AS customer_code,
    date_of_death AS deceased_date
FROM FCBOV.sttms_cust_personal_ee_cu
WHERE date_of_death IS NOT NULL
"""

FLEXCUBE_USER_DETAILS_SQL = """
SELECT
    SUBSTR(u.rec_key, 0, LENGTH(u.rec_key) - 1) AS user_code,
    d.user_name AS user_name,
    u.field_val_1 AS nt_username,
    u.field_val_3 AS id_card_number
FROM fcbov.cstm_function_userdef_fields u
JOIN fcbov.smtb_user d
    ON d.user_id = SUBSTR(u.rec_key, 0, LENGTH(u.rec_key) - 1)
WHERE u.function_id = 'SMDUSRDF'
"""


class FlexcubeDeceasedCustomersStagingJob(OracleToStagingJob):
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
            job_name="flexcube_deceased_customers_staging",
            source_system="flexcube",
            source_object="FCBOV.sttms_cust_personal_ee_cu",
            staging_table="stg_flexcube_deceased_customers",
            sql=FLEXCUBE_DECEASED_CUSTOMERS_SQL,
            requires_window=False,
            timezone=timezone,
        )


class FlexcubeUserDetailsStagingJob(OracleToStagingJob):
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
            job_name="flexcube_user_details_staging",
            source_system="flexcube",
            source_object="FCBOV.CSTM_FUNCTION_USERDEF_FIELDS / FCBOV.SMTB_USER",
            staging_table="stg_flexcube_user_details",
            sql=FLEXCUBE_USER_DETAILS_SQL,
            requires_window=False,
            timezone=timezone,
        )

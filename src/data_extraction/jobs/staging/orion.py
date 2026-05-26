from __future__ import annotations

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.staging.oracle_to_staging import OracleToStagingJob
from data_extraction.staging.writer import StagingWriter


# TODO: Validate account.CURRENCY_ID exists in client ORION schema. If not, adjust to
# actual account currency field.
ORION_ACCOUNTS_SQL = """
SELECT
    account.ACCOUNT_NUMBER AS account_number,
    account.ACCOUNT_DESIGNATION AS acc_designation,
    account_holder.CUSTOMER_CODE AS customer_code,
    currency.DESCRIPTION AS account_currency,
    account.OPENING_DATE AS account_opening_date
FROM ORION.ACCOUNT account
JOIN ORION.ACCOUNT_HOLDER account_holder
    ON account_holder.ACCOUNT_NUMBER = account.ACCOUNT_NUMBER
LEFT JOIN ORION.CURRENCY currency
    ON currency.CURRENCY_ID = account.CURRENCY_ID
"""

ORION_CUSTOMERS_SQL = """
SELECT
    customer.CUSTOMER_CODE AS customer_code,
    customer.MOBILE_TEL AS phone_number,
    personal.ID_CARD AS identification_number,
    ORION.F_CUSTOMER_NAME(customer.CUSTOMER_CODE) AS customer_name,
    personal.DATE_OF_BIRTH AS date_of_birth,
    address.ADDRESS_1 AS address_1,
    address.ADDRESS_2 AS address_2,
    address.CITY AS city,
    address.COUNTRY AS country,
    address.ZIP_CODE AS zip_code
FROM ORION.CUSTOMER customer
LEFT JOIN ORION.PERSONAL_CUSTOMER personal
    ON personal.CUSTOMER_CODE = customer.CUSTOMER_CODE
LEFT JOIN FCUB.CUSTOMER_ADDRESS address
    ON TO_CHAR(customer.CUSTOMER_CODE) = address.FK_CUSTOMERCUST_ID
   AND address.COMMUNICATION_ADDR = '1'
"""

ORION_TRANSACTIONS_SQL = """
SELECT
    tx.USER_TRANSACTION_SERIAL_NUMBER AS transaction_serial_number,
    loan.FIRST_DRAWDOWN_DATE AS first_loan_drawdown_date,
    tx.TRANSACTION_REFERENCE AS transaction_reference,
    channel.SHORT_DESCRIPTION AS channel_lvl_4,
    tx.TRANSACTION_DATE AS transaction_date,
    TO_CHAR(tx.TRANSACTION_TIME, 'HH24:MI') AS transaction_time,
    tx.CHEQUE_NUMBER AS cheque_number,
    tx.DETAILED_STATEMENT_DESC AS detailed_statement_description,
    tx.USER_CODE AS user_code,
    DECODE(
        tx.DR_CR_INDICATOR,
        'D', tx.TRANSACTION_AMOUNT_LM * -1,
        tx.TRANSACTION_AMOUNT_LM
    ) AS amount,
    transaction_code.DESCRIPTION AS transaction_code_description,
    transaction_product.DESCRIPTION AS transaction_product_description,
    tx.ACCOUNT_NUMBER AS account_number
FROM ORION.V_ACC_FINANCIAL_TRANSACTIONS tx
LEFT JOIN ORION.V_CHANNEL_LEVEL_4 channel
    ON channel.CHANNEL_CODE = tx.TRANSACTING_CHANNEL_CODE
LEFT JOIN ORION.TRANSACTION_CODE transaction_code
    ON transaction_code.TRN_CODE = tx.TRN_CODE
LEFT JOIN ORION.TRANSACTION_PRODUCT transaction_product
    ON transaction_product.PRODUCT_CODE = tx.TRANSACTION_PRODUCT_CODE
LEFT JOIN ORION.LOAN loan
    ON loan.ACCOUNT_NUMBER = tx.ACCOUNT_NUMBER
WHERE tx.TRANSACTION_DATE >= TO_DATE(:1, 'YYYY-MM-DD')
  AND tx.TRANSACTION_DATE <  TO_DATE(:2, 'YYYY-MM-DD')
"""

ORION_CUSTOMER_LINKS_SQL = """
SELECT
    customer.CUSTOMER_CODE AS customer_code,
    customer_link.LINKED_CUSTOMER_CODE AS linked_customer_code,
    link_type.DESCRIPTION AS link_type_description
FROM ORION.CUSTOMER customer
JOIN ORION.CUSTOMER_LINK customer_link
    ON customer_link.CUSTOMER_CODE = customer.CUSTOMER_CODE
LEFT JOIN ORION.LINK_TYPE link_type
    ON link_type.LINK_TYPE_CODE = customer_link.LINK_TYPE_CODE
"""

ORION_ADC_ACCESS_SQL = """
SELECT
    account.ACCOUNT_NUMBER AS account_code,
    adc_user.USER_ID AS adc_user_id,
    adc_user.LOGIN_ID AS login_id,
    user_status.DESCRIPTION AS user_status_description,
    third_party_access.DESCRIPTION AS third_party_access_description,
    customer.CUSTOMER_CODE AS customer_code,
    ORION.F_CUSTOMER_NAME(customer.CUSTOMER_CODE) AS customer_name
FROM ORION.CUSTOMER customer
JOIN ORION.ACCOUNT_HOLDER account_holder
    ON account_holder.CUSTOMER_CODE = customer.CUSTOMER_CODE
JOIN ORION.ACCOUNT account
    ON account.ACCOUNT_NUMBER = account_holder.ACCOUNT_NUMBER
JOIN ORION.ADC_CONTRACT adc_contract
    ON adc_contract.CUSTOMER_CODE = customer.CUSTOMER_CODE
JOIN ORION.ADC_USER adc_user
    ON adc_user.CONTRACT_ID = adc_contract.CONTRACT_ID
JOIN ORION.USER_ACC_ASSOCIATION user_account_association
    ON user_account_association.USER_ID = adc_user.USER_ID
JOIN ORION.USER_STATUS user_status
    ON user_status.USER_STATUS_CODE = adc_user.USER_STATUS
JOIN ORION.THIRD_PARTY_ACCESS third_party_access
    ON third_party_access.THIRD_PARTY_ACCESS = user_account_association.THIRD_PARTY_ACCESS
"""

ORION_CUSTOMER_IDENTITY_LOOKUP_SQL = """
SELECT
    ORION.f_customer_identity(eom_customer.CUSTOMER_CODE) AS identification_number,
    eom_customer.CUSTOMER_CODE AS customer_code
FROM ORION.EOM_CUSTOMER eom_customer
"""


class OrionAccountsStagingJob(OracleToStagingJob):
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
            job_name="orion_accounts_staging",
            source_system="orion",
            source_object="ORION.ACCOUNT / ORION.ACCOUNT_HOLDER / ORION.CURRENCY",
            staging_table="stg_orion_accounts",
            sql=ORION_ACCOUNTS_SQL,
            requires_window=False,
            timezone=timezone,
        )


class OrionCustomersStagingJob(OracleToStagingJob):
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
            job_name="orion_customers_staging",
            source_system="orion",
            source_object="ORION.CUSTOMER / ORION.PERSONAL_CUSTOMER / FCUB.CUSTOMER_ADDRESS",
            staging_table="stg_orion_customers",
            sql=ORION_CUSTOMERS_SQL,
            requires_window=False,
            timezone=timezone,
        )


class OrionTransactionsStagingJob(OracleToStagingJob):
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
            job_name="orion_transactions_staging",
            source_system="orion",
            source_object="ORION.V_ACC_FINANCIAL_TRANSACTIONS",
            staging_table="stg_orion_transactions",
            sql=ORION_TRANSACTIONS_SQL,
            requires_window=True,
            timezone=timezone,
        )


class OrionCustomerLinksStagingJob(OracleToStagingJob):
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
            job_name="orion_customer_links_staging",
            source_system="orion",
            source_object="ORION.CUSTOMER_LINK",
            staging_table="stg_orion_customer_links",
            sql=ORION_CUSTOMER_LINKS_SQL,
            requires_window=False,
            timezone=timezone,
        )


class OrionAdcAccessStagingJob(OracleToStagingJob):
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
            job_name="orion_adc_access_staging",
            source_system="orion",
            source_object="ORION ADC access tables",
            staging_table="stg_orion_adc_access",
            sql=ORION_ADC_ACCESS_SQL,
            requires_window=False,
            timezone=timezone,
        )


class OrionCustomerIdentityLookupStagingJob(OracleToStagingJob):
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
            job_name="orion_customer_identity_lookup_staging",
            source_system="orion",
            source_object="ORION.EOM_CUSTOMER",
            staging_table="stg_orion_customer_identity_lookup",
            sql=ORION_CUSTOMER_IDENTITY_LOOKUP_SQL,
            requires_window=False,
            timezone=timezone,
        )

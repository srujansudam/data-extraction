from __future__ import annotations

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult


LOANS_SQL = """
SELECT DISTINCT
    loan.ACCOUNT_NUMBER AS account_number,
    account_holder.CUSTOMER_CODE AS customer_code,
    product_level_6.DESCRIPTION AS product_lvl_6,
    product_level_7.DESCRIPTION AS product_lvl_7,
    loan.DRAWNDOWN_EXPIRY_DATE AS drawdown_expiry_date
FROM ORION.LOAN loan
JOIN ORION.ADVANCE advance
    ON advance.ACCOUNT_NUMBER = loan.ACCOUNT_NUMBER
JOIN ORION.AGREEMENT agreement
    ON agreement.AGREEMENT_NUMBER = advance.AGREEMENT_NUMBER
JOIN ORION.ACCOUNT account
    ON account.ACCOUNT_NUMBER = advance.ACCOUNT_NUMBER
JOIN ORION.ACCOUNT_HOLDER account_holder
    ON account_holder.ACCOUNT_NUMBER = account.ACCOUNT_NUMBER
LEFT JOIN ORION.V_PRODUCT_LEVEL_7 product_level_7
    ON product_level_7.PRODUCT_CODE = account.PRODUCT_CODE
LEFT JOIN ORION.V_PRODUCT_LEVEL_6 product_level_6
    ON product_level_6.PRODUCT_CODE = product_level_7.PRODUCT_PARENT_CODE
"""


class LoansExtractionJob(BaseExtractionJob):
    job_name = "loans"
    source_system = "orion"
    target_table = "loans"

    def __init__(
        self,
        db: DatabaseAdapter,
        source_client: SourceQueryClient,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(db=db, timezone=timezone)
        self.source_client = source_client

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        rows = self.source_client.query_all(LOANS_SQL)

        insert_rows = [
            [
                row.get("account_number"),
                row.get("customer_code"),
                row.get("product_lvl_6"),
                row.get("product_lvl_7"),
                row.get("drawdown_expiry_date"),
            ]
            for row in rows
        ]

        self.db.execute("DELETE FROM loans")

        self.db.execute_many(
            """
            INSERT INTO loans (
                account_number,
                customer_code,
                product_lvl_6,
                product_lvl_7,
                drawdown_expiry_date
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            insert_rows,
        )
        self.db.commit()

        return JobResult(
            rows_extracted=len(rows),
            rows_inserted=len(insert_rows),
            rows_updated=0,
            rows_rejected=0,
        )

from __future__ import annotations

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult


OFFICE_ACCOUNTS_SQL = """
SELECT
    CUST_AC_NO AS office_account_number,
    CUST_NO AS customer_code,
    AC_DESC AS office_account_name
FROM FCBOV.STTM_CUST_ACCOUNT
WHERE ACCOUNT_CLASS LIKE '%OFF%'
"""


class OfficeAccountsExtractionJob(BaseExtractionJob):
    job_name = "office_accounts"
    source_system = "flexcube"
    target_table = "office_accounts"

    def __init__(
        self,
        db: DatabaseAdapter,
        source_client: SourceQueryClient,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(db=db, timezone=timezone)
        self.source_client = source_client

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        rows = self.source_client.query_all(OFFICE_ACCOUNTS_SQL)

        # office_accounts is a current snapshot reference table.
        # Refresh the table each run from the source.
        self.db.execute("DELETE FROM office_accounts")

        insert_rows = [
            [
                row.get("office_account_number"),
                row.get("customer_code"),
                row.get("office_account_name"),
            ]
            for row in rows
        ]

        self.db.execute_many(
            """
            INSERT INTO office_accounts (
                office_account_number,
                customer_code,
                office_account_name
            )
            VALUES (?, ?, ?)
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
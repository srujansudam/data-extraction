from __future__ import annotations

from typing import Any

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult


EOM_BOOK_BALANCE_SQL = """
SELECT
    eom_account.EOM_DATE AS eom_date,
    eom_customer.CUSTOMER_CODE AS customer_code,
    eom_account.ACCOUNT_NUMBER AS account_number,
    product_level_7.DESCRIPTION AS product_lvl_7,
    eom_account.BOOK_BALANCE_LM AS book_balance
FROM ORION.EOM_ACCOUNT eom_account
JOIN ORION.EOM_ACCOUNT_HOLDER account_holder
    ON account_holder.ACCOUNT_NUMBER = eom_account.ACCOUNT_NUMBER
    AND account_holder.EOM_DATE = eom_account.EOM_DATE
JOIN ORION.EOM_CUSTOMER eom_customer
    ON eom_customer.CUSTOMER_CODE = account_holder.CUSTOMER_CODE
    AND eom_customer.EOM_DATE = account_holder.EOM_DATE
LEFT JOIN ORION.EOM_V_PRODUCT_LEVEL_7 product_level_7
    ON product_level_7.PRODUCT_CODE = eom_account.PRODUCT_CODE
    AND product_level_7.EOM_DATE = eom_account.EOM_DATE
WHERE eom_account.EOM_DATE >= ADD_MONTHS(TRUNC(SYSDATE), -24)
"""


class EomBookBalanceExtractionJob(BaseExtractionJob):
    job_name = "eom_book_balance"
    source_system = "orion"
    target_table = "eom_book_balance"

    def __init__(
        self,
        db: DatabaseAdapter,
        source_client: SourceQueryClient,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(db=db, timezone=timezone)
        self.source_client = source_client

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        rows = self.source_client.query_all(EOM_BOOK_BALANCE_SQL)
        insert_rows = _deduplicate_rows_by_key(
            [
                [
                    row.get("eom_date"),
                    row.get("customer_code"),
                    row.get("account_number"),
                    row.get("product_lvl_7"),
                    row.get("book_balance"),
                ]
                for row in rows
            ]
        )

        for row in insert_rows:
            self.db.execute(
                """
                DELETE FROM eom_book_balance
                WHERE eom_date = ?
                    AND customer_code = ?
                    AND account_number = ?
                """,
                row[:3],
            )

        self.db.execute_many(
            """
            INSERT INTO eom_book_balance (
                eom_date,
                customer_code,
                account_number,
                product_lvl_7,
                book_balance
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


def _deduplicate_rows_by_key(rows: list[list[Any]]) -> list[list[Any]]:
    deduplicated_rows = []
    seen = set()

    for row in rows:
        row_key = tuple(row[:3])
        if row_key in seen:
            continue

        seen.add(row_key)
        deduplicated_rows.append(row)

    return deduplicated_rows

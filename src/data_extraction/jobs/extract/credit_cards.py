from __future__ import annotations

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult


CREDIT_CARDS_SQL = """
SELECT
    rt.TRN_REF_NO AS transaction_reference,
    rt.MAKER_ID AS user_code,
    rt.TRN_DT AS date,
    rtc.CUSTOMER_NO AS customer_code,
    SUBSTR(rt.TRN_REF_NO, 1, 3) AS branch_code,
    NULL AS amount,
    rtc.CREDIT_CARD_NO AS credit_card_number
FROM fcbov.DETB_RTL_TELLER_EE_CU rtc
JOIN fcbov.DETB_RTL_TELLER rt
    ON rt.XREF = rtc.XREF
JOIN fcbov.CSTM_PRODUCT p
    ON p.PRODUCT_CODE = rt.PRODUCT_CODE
WHERE rtc.NATIONAL_ID IS NOT NULL
  AND rtc.CREDIT_CARD_NO IS NOT NULL
  AND SUBSTR(rt.TRN_REF_NO, 1, 3) = '301'
  AND rt.TRN_DT >= TO_DATE(:1, 'YYYY-MM-DD')
  AND rt.TRN_DT <  TO_DATE(:2, 'YYYY-MM-DD')
"""


class CreditCardsExtractionJob(BaseExtractionJob):
    job_name = "credit_cards"
    source_system = "flexcube"
    target_table = "credit_cards"

    def __init__(
        self,
        db: DatabaseAdapter,
        source_client: SourceQueryClient,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(db=db, timezone=timezone)
        self.source_client = source_client

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        if window_start is None or window_end is None:
            raise ValueError("credit_cards extraction requires window_start and window_end.")

        start_date = window_start[:10]
        end_date = window_end[:10]
        rows = self.source_client.query_all(CREDIT_CARDS_SQL, [start_date, end_date])

        insert_rows = [
            [
                row.get("transaction_reference"),
                row.get("user_code"),
                row.get("date"),
                row.get("customer_code"),
                row.get("branch_code"),
                None,
                row.get("credit_card_number"),
            ]
            for row in rows
        ]

        if not insert_rows:
            return JobResult(
                rows_extracted=len(rows),
                rows_inserted=0,
                rows_updated=0,
                rows_rejected=0,
            )

        for row in insert_rows:
            self.db.execute(
                "DELETE FROM credit_cards WHERE transaction_reference = ?",
                [row[0]],
            )

        self.db.execute_many(
            """
            INSERT INTO credit_cards (
                transaction_reference,
                user_code,
                date,
                customer_code,
                branch_code,
                amount,
                credit_card_number
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
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

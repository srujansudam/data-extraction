from __future__ import annotations

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult


EXCHANGE_RATE_SQL = """
SELECT
    CONTRACT_REF_NO AS transaction_id,
    CUSTOMER_NO AS customer_code,
    CCY_BASE AS base_currency,
    TYPE_OPER AS transaction_type,
    BRN AS branch,
    AMOUNT_TRN AS amount,
    CCY_TRN AS transaction_currency,
    EX_RATE AS exchange_rate,
    MID_RATE AS middle_rate,
    TRN_DT AS transaction_date
FROM FCCREAD.BVTB_FXBV128_HIST
WHERE TRN_DT >= TO_DATE(:1, 'YYYY-MM-DD')
  AND TRN_DT <  TO_DATE(:2, 'YYYY-MM-DD')
"""


class ExchangeRateExtractionJob(BaseExtractionJob):
    job_name = "exchange_rate"
    source_system = "flexcube"
    target_table = "exchange_rate"

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
            raise ValueError("exchange_rate extraction requires window_start and window_end.")

        start_date = window_start[:10]
        end_date = window_end[:10]
        rows = self.source_client.query_all(EXCHANGE_RATE_SQL, [start_date, end_date])

        insert_rows = [
            [
                row.get("transaction_id"),
                row.get("customer_code"),
                row.get("base_currency"),
                row.get("transaction_type"),
                row.get("branch"),
                row.get("amount"),
                row.get("transaction_currency"),
                row.get("exchange_rate"),
                row.get("middle_rate"),
                row.get("transaction_date"),
            ]
            for row in rows
        ]

        for row in insert_rows:
            self.db.execute(
                "DELETE FROM exchange_rate WHERE transaction_id = ?",
                [row[0]],
            )

        self.db.execute_many(
            """
            INSERT INTO exchange_rate (
                transaction_id,
                customer_code,
                base_currency,
                transaction_type,
                branch,
                amount,
                transaction_currency,
                exchange_rate,
                middle_rate,
                transaction_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

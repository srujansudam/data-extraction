from __future__ import annotations

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob, JobResult


DORMANT_ACCOUNT_SQL = """
SELECT
    cust_ac_no AS account_number,
    NULL AS date,
    ac_stat_dormant AS dormant
FROM fcbov.sttm_account_balance
WHERE ac_stat_dormant = 'Y'
"""


class DormantAccountExtractionJob(BaseExtractionJob):
    job_name = "dormant_account"
    source_system = "flexcube"
    target_table = "dormant_account"

    def __init__(
        self,
        db: DatabaseAdapter,
        source_client: SourceQueryClient,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(db=db, timezone=timezone)
        self.source_client = source_client

    def execute(self, window_start: str | None, window_end: str | None) -> JobResult:
        rows = self.source_client.query_all(DORMANT_ACCOUNT_SQL)

        # Requirement: full snapshot daily, duplicates allowed.
        # So we do not delete old rows and do not deduplicate here.
        insert_rows = [
            [
                row.get("account_number"),
                row.get("date"),
                row.get("dormant"),
            ]
            for row in rows
        ]

        self.db.execute_many(
            """
            INSERT INTO dormant_account (
                account_number,
                date,
                dormant
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
from __future__ import annotations

from typing import Any

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.transform.base import BaseTransformJob, TransformResult


class AccountDataTransformJob(BaseTransformJob):
    job_name = "transform_account_data"
    target_table = "account_data"
    source_system = "internal"

    def __init__(
        self,
        db: DatabaseAdapter,
        staging_reader: StagingReader,
        timezone: str = "Europe/Malta",
    ) -> None:
        super().__init__(db=db, timezone=timezone)
        self.staging_reader = staging_reader

    def execute_transform(
        self,
        run_id: int,
        window_start: str | None,
        window_end: str | None,
    ) -> TransformResult:
        rows = self.staging_reader.read_payloads("stg_orion_accounts", run_id=run_id)
        insert_rows = _deduplicate_account_rows(rows)

        self.db.execute("DELETE FROM account_data")
        self.db.execute_many(
            """
            INSERT INTO account_data (
                account_number,
                account_currency,
                acc_designation,
                customer_code
            )
            VALUES (?, ?, ?, ?)
            """,
            insert_rows,
        )
        self.db.commit()

        return TransformResult(
            rows_read=len(rows),
            rows_inserted=len(insert_rows),
            rows_updated=0,
            rows_rejected=0,
        )


def _deduplicate_account_rows(rows: list[dict[str, Any]]) -> list[list[Any]]:
    insert_rows = []
    seen = set()

    for row in rows:
        row_key = (row.get("account_number"), row.get("customer_code"))
        if row_key in seen:
            continue

        seen.add(row_key)
        insert_rows.append(
            [
                row.get("account_number"),
                row.get("account_currency"),
                row.get("acc_designation"),
                row.get("customer_code"),
            ]
        )

    return insert_rows

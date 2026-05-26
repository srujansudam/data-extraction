from __future__ import annotations

from typing import Any

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.transform.base import BaseTransformJob, TransformResult


class ThirdPartyAccessTransformJob(BaseTransformJob):
    job_name = "transform_third_party_access"
    target_table = "third_party_access"
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
        adc_access_rows = self.staging_reader.read_payloads("stg_orion_adc_access", run_id=run_id)
        insert_rows = _build_third_party_access_rows(adc_access_rows)

        self.db.execute("DELETE FROM third_party_access")
        self.db.execute_many(
            """
            INSERT INTO third_party_access (
                customer_code,
                account_code
            )
            VALUES (?, ?)
            """,
            insert_rows,
        )
        self.db.commit()

        return TransformResult(
            rows_read=len(adc_access_rows),
            rows_inserted=len(insert_rows),
            rows_updated=0,
            rows_rejected=0,
        )


def _build_third_party_access_rows(adc_access_rows: list[dict[str, Any]]) -> list[list[Any]]:
    insert_rows = []
    seen = set()

    for row in adc_access_rows:
        customer_code = row.get("customer_code")
        account_code = row.get("account_code") or row.get("account_number")
        if customer_code is None or account_code is None:
            continue

        row_key = (customer_code, account_code)
        if row_key in seen:
            continue

        seen.add(row_key)
        insert_rows.append([customer_code, account_code])

    return insert_rows

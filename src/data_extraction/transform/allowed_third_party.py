from __future__ import annotations

from typing import Any

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.transform.base import BaseTransformJob, TransformResult


class AllowedThirdPartyTransformJob(BaseTransformJob):
    job_name = "transform_allowed_third_party"
    target_table = "allowed_third_party"
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
        customer_links = self.staging_reader.read_payloads("stg_orion_customer_links", run_id=run_id)
        accounts = self.staging_reader.read_payloads("stg_orion_accounts", run_id=run_id)
        # Current implementation uses ORION customer links as the allowed-party source based on
        # the available scenario mapping. If a separate mandate/allowed-access source is provided
        # later, replace or augment this transform.
        insert_rows = _build_allowed_third_party_rows(customer_links, accounts)

        self.db.execute("DELETE FROM allowed_third_party")
        self.db.execute_many(
            """
            INSERT INTO allowed_third_party (
                customer_code,
                account_code,
                reason
            )
            VALUES (?, ?, ?)
            """,
            insert_rows,
        )
        self.db.commit()

        return TransformResult(
            rows_read=len(customer_links),
            rows_inserted=len(insert_rows),
            rows_updated=0,
            rows_rejected=0,
        )


def _build_allowed_third_party_rows(
    customer_links: list[dict[str, Any]],
    accounts: list[dict[str, Any]],
) -> list[list[Any]]:
    accounts_by_customer = _accounts_by_customer(accounts)
    insert_rows = []
    seen = set()

    for link in customer_links:
        customer_code = link.get("customer_code")
        if customer_code is None:
            continue

        reason = link.get("link_type_description")
        account_numbers = accounts_by_customer.get(customer_code) or [None]
        for account_number in account_numbers:
            row_key = (customer_code, account_number, reason)
            if row_key in seen:
                continue

            seen.add(row_key)
            insert_rows.append([customer_code, account_number, reason])

    return insert_rows


def _accounts_by_customer(accounts: list[dict[str, Any]]) -> dict[Any, list[Any]]:
    accounts_by_customer: dict[Any, list[Any]] = {}
    for account in accounts:
        customer_code = account.get("customer_code")
        account_number = account.get("account_number")
        if customer_code is None:
            continue

        accounts_by_customer.setdefault(customer_code, []).append(account_number)

    return accounts_by_customer

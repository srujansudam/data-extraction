from __future__ import annotations

from typing import Any

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.transform.base import BaseTransformJob, TransformResult


class LegalRulingsTransformJob(BaseTransformJob):
    job_name = "transform_legal_rulings"
    target_table = "legal_rulings"
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
        legal_rulings = self.staging_reader.read_payloads("stg_lotus_legal_rulings", run_id=run_id)
        accounts = self.staging_reader.read_payloads("stg_orion_accounts", run_id=run_id)
        accounts_by_customer = _accounts_by_customer(accounts)
        insert_rows = _build_legal_ruling_rows(legal_rulings, accounts_by_customer)

        self.db.execute("DELETE FROM legal_rulings")
        self.db.execute_many(
            """
            INSERT INTO legal_rulings (
                deceased_customer_code,
                deceased_account_number,
                ruling_holder_ID
            )
            VALUES (?, ?, ?)
            """,
            insert_rows,
        )
        self.db.commit()

        return TransformResult(
            rows_read=len(legal_rulings),
            rows_inserted=len(insert_rows),
            rows_updated=0,
            rows_rejected=0,
        )


def _build_legal_ruling_rows(
    legal_rulings: list[dict[str, Any]],
    accounts_by_customer: dict[Any, list[Any]],
) -> list[list[Any]]:
    insert_rows = []
    seen = set()

    for ruling in legal_rulings:
        deceased_customer_code = _first_present(
            ruling,
            ["Deceased Customer Code", "deceased_customer_code"],
        )
        ruling_holder_id = _first_present(
            ruling,
            ["ID Card No", "ID Card No / Ref No", "ruling_holder_ID", "id_card_no"],
        )

        for account_number in accounts_by_customer.get(deceased_customer_code, []):
            row_key = (deceased_customer_code, account_number, ruling_holder_id)
            if row_key in seen:
                continue

            seen.add(row_key)
            insert_rows.append([deceased_customer_code, account_number, ruling_holder_id])

    return insert_rows


def _accounts_by_customer(accounts: list[dict[str, Any]]) -> dict[Any, list[Any]]:
    accounts_by_customer: dict[Any, list[Any]] = {}

    for account in accounts:
        customer_code = account.get("customer_code")
        account_number = account.get("account_number")
        if customer_code is None or account_number is None:
            continue

        accounts_by_customer.setdefault(customer_code, []).append(account_number)

    return accounts_by_customer


def _first_present(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value

    return None

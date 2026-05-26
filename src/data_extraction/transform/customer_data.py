from __future__ import annotations

from datetime import date
from typing import Any

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.transform.base import BaseTransformJob, TransformResult


class CustomerDataTransformJob(BaseTransformJob):
    job_name = "transform_customer_data"
    target_table = "customer_data"
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
        customers = self.staging_reader.read_payloads("stg_orion_customers", run_id=run_id)
        accounts = self.staging_reader.read_payloads("stg_orion_accounts", run_id=run_id)
        deceased_customers = self.staging_reader.read_payloads(
            "stg_flexcube_deceased_customers",
            run_id=run_id,
        )

        extraction_date = _extraction_date(window_end)
        account_opening_dates = _earliest_account_opening_dates(accounts)
        deceased_dates = {
            row.get("customer_code"): row.get("deceased_date")
            for row in deceased_customers
            if row.get("customer_code") is not None
        }
        insert_rows = _build_customer_rows(
            customers=customers,
            account_opening_dates=account_opening_dates,
            deceased_dates=deceased_dates,
            extraction_date=extraction_date,
        )

        self.db.execute("DELETE FROM customer_data")
        self.db.execute_many(
            """
            INSERT INTO customer_data (
                customer_code,
                phone_number,
                creation_date,
                identification_number,
                customer_name,
                customer_address,
                age,
                deceased_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            insert_rows,
        )
        self.db.commit()

        return TransformResult(
            rows_read=len(customers) + len(accounts) + len(deceased_customers),
            rows_inserted=len(insert_rows),
            rows_updated=0,
            rows_rejected=0,
        )


def _build_customer_rows(
    customers: list[dict[str, Any]],
    account_opening_dates: dict[Any, Any],
    deceased_dates: dict[Any, Any],
    extraction_date: date,
) -> list[list[Any]]:
    insert_rows = []
    seen_customer_codes = set()

    for customer in customers:
        customer_code = customer.get("customer_code")
        if customer_code in seen_customer_codes:
            continue

        seen_customer_codes.add(customer_code)
        insert_rows.append(
            [
                customer_code,
                customer.get("phone_number"),
                account_opening_dates.get(customer_code),
                customer.get("identification_number"),
                customer.get("customer_name"),
                _customer_address(customer),
                _calculate_age(customer.get("date_of_birth"), extraction_date),
                deceased_dates.get(customer_code),
            ]
        )

    return insert_rows


def _customer_address(customer: dict[str, Any]) -> str | None:
    address_parts = [
        customer.get("address_1"),
        customer.get("address_2"),
        customer.get("city"),
        customer.get("country"),
        customer.get("zip_code"),
    ]
    non_empty_parts = [str(part) for part in address_parts if part not in (None, "")]
    if not non_empty_parts:
        return None

    return ", ".join(non_empty_parts)


def _earliest_account_opening_dates(accounts: list[dict[str, Any]]) -> dict[Any, Any]:
    opening_dates: dict[Any, Any] = {}

    for account in accounts:
        customer_code = account.get("customer_code")
        opening_date = account.get("account_opening_date")
        if customer_code is None or opening_date in (None, ""):
            continue

        if customer_code not in opening_dates or str(opening_date) < str(opening_dates[customer_code]):
            opening_dates[customer_code] = opening_date

    return opening_dates


def _extraction_date(window_end: str | None) -> date:
    if window_end is None:
        return date.today()

    return date.fromisoformat(window_end[:10])


def _calculate_age(date_of_birth: Any, extraction_date: date) -> int | None:
    if date_of_birth in (None, ""):
        return None

    try:
        birth_date = date.fromisoformat(str(date_of_birth)[:10])
    except ValueError:
        return None

    age = extraction_date.year - birth_date.year
    birthday_this_year = birth_date.replace(year=extraction_date.year)
    if extraction_date < birthday_this_year:
        age -= 1

    return age

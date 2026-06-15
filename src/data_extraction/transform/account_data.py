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
        insert_rows = _build_canonical_account_rows(rows)
        association_rows = _build_account_association_rows(
            rows,
            run_id=run_id,
            extracted_at=window_end,
        )

        self.db.execute("DELETE FROM account_data")
        self.db.execute("DELETE FROM account_customer_association")
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
        self.db.execute_many(
            """
            INSERT INTO account_customer_association (
                account_number,
                customer_code,
                relationship_type,
                source_system,
                source_run_id,
                extracted_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            association_rows,
        )
        self.db.commit()

        return TransformResult(
            rows_read=len(rows),
            rows_inserted=len(insert_rows),
            rows_updated=0,
            rows_rejected=0,
        )


def _build_canonical_account_rows(rows: list[dict[str, Any]]) -> list[list[Any]]:
    rows_by_account: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        account_number = row.get("account_number")
        if not _has_value(account_number):
            continue

        rows_by_account.setdefault(account_number, []).append(row)

    insert_rows = []
    for account_number in sorted(rows_by_account, key=_value_sort_key):
        account_rows = rows_by_account[account_number]
        insert_rows.append(
            [
                account_number,
                _preferred_value(account_rows, "account_currency"),
                _preferred_value(account_rows, "acc_designation"),
                _preferred_value(account_rows, "customer_code"),
            ]
        )

    return insert_rows


def _build_account_association_rows(
    rows: list[dict[str, Any]],
    run_id: int,
    extracted_at: str | None,
) -> list[list[Any]]:
    relationships: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
    for row in rows:
        account_number = row.get("account_number")
        customer_code = row.get("customer_code")
        if not _has_value(account_number) or not _has_value(customer_code):
            continue

        relationships.setdefault((account_number, customer_code), []).append(row)

    association_rows = []
    for account_number, customer_code in sorted(
        relationships,
        key=lambda relationship: (
            _value_sort_key(relationship[0]),
            _value_sort_key(relationship[1]),
        ),
    ):
        relationship_rows = relationships[(account_number, customer_code)]
        association_rows.append(
            [
                account_number,
                customer_code,
                _preferred_value(relationship_rows, "relationship_type"),
                "orion",
                str(run_id),
                extracted_at,
            ]
        )

    return association_rows


def _preferred_value(rows: list[dict[str, Any]], field_name: str) -> Any:
    values = [row.get(field_name) for row in rows if _has_value(row.get(field_name))]
    if not values:
        return None

    return min(values, key=_value_sort_key)


def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _value_sort_key(value: Any) -> tuple[str, str]:
    return (str(value).casefold(), str(value))

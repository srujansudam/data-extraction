from __future__ import annotations

from typing import Any

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.transform.base import BaseTransformJob, TransformResult


class TransactionDataTransformJob(BaseTransformJob):
    job_name = "transform_transaction_data"
    target_table = "transaction_data"
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
        rows = self.staging_reader.read_payloads("stg_orion_transactions", run_id=run_id)
        insert_rows = _deduplicate_transaction_rows(rows)

        for row in insert_rows:
            self.db.execute(
                "DELETE FROM transaction_data WHERE transaction_serial_number = ?",
                [row[0]],
            )

        self.db.execute_many(
            """
            INSERT INTO transaction_data (
                transaction_serial_number,
                first_loan_drawdown_date,
                transaction_reference,
                channel_lvl_4,
                transaction_date_time,
                cheque_number,
                detailed_statement_description,
                user_code,
                amount,
                transaction_code_description,
                transaction_product_description,
                account_number,
                initiator_id,
                statement_description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def _deduplicate_transaction_rows(rows: list[dict[str, Any]]) -> list[list[Any]]:
    insert_rows = []
    seen = set()

    for row in rows:
        transaction_serial_number = row.get("transaction_serial_number")
        if transaction_serial_number in seen:
            continue

        seen.add(transaction_serial_number)
        insert_rows.append(
            [
                transaction_serial_number,
                row.get("first_loan_drawdown_date"),
                row.get("transaction_reference"),
                row.get("channel_lvl_4"),
                _transaction_date_time(row),
                row.get("cheque_number"),
                row.get("detailed_statement_description"),
                row.get("user_code"),
                row.get("amount"),
                row.get("transaction_code_description"),
                row.get("transaction_product_description"),
                row.get("account_number"),
                None,
                None,
            ]
        )

    return insert_rows


def _transaction_date_time(row: dict[str, Any]) -> str | None:
    transaction_date = row.get("transaction_date")
    transaction_time = row.get("transaction_time")

    if transaction_date and transaction_time:
        return f"{transaction_date} {transaction_time}"
    if transaction_date:
        return str(transaction_date)

    return None

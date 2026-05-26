from __future__ import annotations

from typing import Any

from data_extraction.transform.base import BaseTransformJob, TransformResult


class UsersTransformJob(BaseTransformJob):
    job_name = "transform_users"
    target_table = "users"
    source_system = "internal"

    def execute_transform(
        self,
        run_id: int,
        window_start: str | None,
        window_end: str | None,
    ) -> TransformResult:
        staff_rows = self.db.query_all(
            """
            SELECT user_code, customer_code, id_card_number, account_number,
                   departure_date, departure_details, location
            FROM staff
            ORDER BY user_code, customer_code, account_number
            """
        )
        insert_rows = _deduplicate_user_rows(staff_rows)

        self.db.execute("DELETE FROM users")
        self.db.execute_many(
            """
            INSERT INTO users (
                user_code,
                customer_code,
                id_card_number,
                account_number,
                departure_date,
                departure_details,
                location
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            insert_rows,
        )
        self.db.commit()

        return TransformResult(
            rows_read=len(staff_rows),
            rows_inserted=len(insert_rows),
            rows_updated=0,
            rows_rejected=0,
        )


def _deduplicate_user_rows(staff_rows: list[dict[str, Any]]) -> list[list[Any]]:
    insert_rows = []
    seen = set()
    for row in staff_rows:
        row_key = (row.get("user_code"), row.get("customer_code"), row.get("account_number"))
        if row_key in seen:
            continue
        seen.add(row_key)
        insert_rows.append(
            [
                row.get("user_code"),
                row.get("customer_code"),
                row.get("id_card_number"),
                row.get("account_number"),
                row.get("departure_date"),
                row.get("departure_details"),
                row.get("location"),
            ]
        )
    return insert_rows

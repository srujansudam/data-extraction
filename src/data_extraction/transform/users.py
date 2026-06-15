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
        insert_rows = _build_canonical_user_rows(staff_rows)
        association_rows = _build_user_association_rows(
            staff_rows,
            run_id=run_id,
            extracted_at=window_end,
        )

        self.db.execute("DELETE FROM users")
        self.db.execute("DELETE FROM user_customer_account_association")
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
        self.db.execute_many(
            """
            INSERT INTO user_customer_account_association (
                user_code,
                customer_code,
                account_number,
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
            rows_read=len(staff_rows),
            rows_inserted=len(insert_rows),
            rows_updated=0,
            rows_rejected=0,
        )


def _build_canonical_user_rows(staff_rows: list[dict[str, Any]]) -> list[list[Any]]:
    rows_by_user: dict[Any, list[dict[str, Any]]] = {}
    for row in staff_rows:
        user_code = row.get("user_code")
        if not _has_value(user_code):
            continue

        rows_by_user.setdefault(user_code, []).append(row)

    insert_rows = []
    for user_code in sorted(rows_by_user, key=_value_sort_key):
        user_rows = rows_by_user[user_code]
        customer_code, account_number = _representative_relationship(user_rows)
        insert_rows.append(
            [
                user_code,
                customer_code,
                _preferred_value(user_rows, "id_card_number"),
                account_number,
                _preferred_value(user_rows, "departure_date"),
                _preferred_value(user_rows, "departure_details"),
                _preferred_value(user_rows, "location"),
            ]
        )

    return insert_rows


def _build_user_association_rows(
    staff_rows: list[dict[str, Any]],
    run_id: int,
    extracted_at: str | None,
) -> list[list[Any]]:
    relationships = {
        (row.get("user_code"), row.get("customer_code"), row.get("account_number"))
        for row in staff_rows
        if _has_value(row.get("user_code"))
    }

    return [
        [user_code, customer_code, account_number, "internal", str(run_id), extracted_at]
        for user_code, customer_code, account_number in sorted(
            relationships,
            key=_relationship_sort_key,
        )
    ]


def _representative_relationship(rows: list[dict[str, Any]]) -> tuple[Any, Any]:
    relationships = {
        (row.get("customer_code"), row.get("account_number"))
        for row in rows
        if _has_value(row.get("customer_code")) or _has_value(row.get("account_number"))
    }
    if not relationships:
        return None, None

    return min(
        relationships,
        key=lambda relationship: (
            _nullable_value_sort_key(relationship[0]),
            _nullable_value_sort_key(relationship[1]),
        ),
    )


def _preferred_value(rows: list[dict[str, Any]], field_name: str) -> Any:
    values = [row.get(field_name) for row in rows if _has_value(row.get(field_name))]
    if not values:
        return None

    return min(values, key=_value_sort_key)


def _relationship_sort_key(
    relationship: tuple[Any, Any, Any],
) -> tuple[tuple[int, str, str], tuple[int, str, str], tuple[int, str, str]]:
    return (
        _nullable_value_sort_key(relationship[0]),
        _nullable_value_sort_key(relationship[1]),
        _nullable_value_sort_key(relationship[2]),
    )


def _nullable_value_sort_key(value: Any) -> tuple[int, str, str]:
    if not _has_value(value):
        return (1, "", "")

    value_key = _value_sort_key(value)
    return (0, value_key[0], value_key[1])


def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _value_sort_key(value: Any) -> tuple[str, str]:
    return (str(value).casefold(), str(value))

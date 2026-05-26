from __future__ import annotations

from typing import Any

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.transform.base import BaseTransformJob, TransformResult


class RelatedPartiesTransformJob(BaseTransformJob):
    job_name = "transform_related_parties"
    target_table = "related_parties"
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
        hris_rows = self.staging_reader.read_payloads(
            "stg_hris_personnel_contact_detail", run_id=run_id
        )
        customer_links = self.staging_reader.read_payloads("stg_orion_customer_links", run_id=run_id)
        flexcube_users = self.staging_reader.read_payloads("stg_flexcube_user_details", run_id=run_id)
        identity_rows = self.staging_reader.read_payloads(
            "stg_orion_customer_identity_lookup", run_id=run_id
        )

        insert_rows = _build_related_party_rows(
            hris_rows=hris_rows,
            customer_links=customer_links,
            flexcube_users=flexcube_users,
            identity_rows=identity_rows,
        )

        self.db.execute("DELETE FROM related_parties")
        self.db.execute_many(
            """
            INSERT INTO related_parties (
                user_code,
                customer_code
            )
            VALUES (?, ?)
            """,
            insert_rows,
        )
        self.db.commit()

        return TransformResult(
            rows_read=len(hris_rows) + len(customer_links),
            rows_inserted=len(insert_rows),
            rows_updated=0,
            rows_rejected=0,
        )


def _build_related_party_rows(
    hris_rows: list[dict[str, Any]],
    customer_links: list[dict[str, Any]],
    flexcube_users: list[dict[str, Any]],
    identity_rows: list[dict[str, Any]],
) -> list[list[Any]]:
    user_by_id = {
        _normalized(_get(row, ["id_card_number"])): _get(row, ["user_code"])
        for row in flexcube_users
        if _get(row, ["id_card_number"]) is not None
    }
    customer_by_id = {
        _normalized(_get(row, ["identification_number"])): _get(row, ["customer_code"])
        for row in identity_rows
        if _get(row, ["identification_number"]) is not None
    }
    identity_by_customer = {
        _get(row, ["customer_code"]): _get(row, ["identification_number"])
        for row in identity_rows
        if _get(row, ["customer_code"]) is not None
    }

    rows = []
    seen = set()
    for hris_row in hris_rows:
        user_code = user_by_id.get(_normalized(_get(hris_row, ["National ID", "national_id"])))
        customer_code = customer_by_id.get(
            _normalized(_get(hris_row, ["Rel National ID", "rel_national_id"]))
        )
        _append_if_complete(rows, seen, user_code, customer_code)

    for link in customer_links:
        customer_code = _get(link, ["customer_code"])
        staff_identity = identity_by_customer.get(customer_code)
        user_code = user_by_id.get(_normalized(staff_identity))
        linked_customer_code = _get(link, ["linked_customer_code"])
        _append_if_complete(rows, seen, user_code, linked_customer_code)

    return rows


def _append_if_complete(
    rows: list[list[Any]],
    seen: set[tuple[Any, Any]],
    user_code: Any,
    customer_code: Any,
) -> None:
    if user_code is None or customer_code is None:
        return
    row_key = (user_code, customer_code)
    if row_key in seen:
        return
    seen.add(row_key)
    rows.append([user_code, customer_code])


def _get(row: dict[str, Any], keys: list[str]) -> Any:
    normalized = {_normalized(key): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(_normalized(key))
        if value not in (None, ""):
            return value
    return None


def _normalized(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")

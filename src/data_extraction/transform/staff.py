from __future__ import annotations

from typing import Any

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.transform.base import BaseTransformJob, TransformResult


class StaffTransformJob(BaseTransformJob):
    job_name = "transform_staff"
    target_table = "staff"
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
        hris_consolidated = self.staging_reader.read_payloads(
            "stg_hris_consolidated", run_id=run_id
        )
        staff_identification = hris_consolidated
        appendix_rows: list[dict[str, Any]] = []
        if not hris_consolidated:
            staff_identification = self.staging_reader.read_payloads(
                "stg_hris_staff_identification", run_id=run_id
            )
            appendix_rows = self.staging_reader.read_payloads(
                "stg_hris_appendix_3_crm", run_id=run_id
            )
        lotus_rows = self.staging_reader.read_payloads("stg_lotus_bov_employees", run_id=run_id)
        flexcube_users = self.staging_reader.read_payloads("stg_flexcube_user_details", run_id=run_id)
        identity_rows = self.staging_reader.read_payloads(
            "stg_orion_customer_identity_lookup", run_id=run_id
        )
        account_rows = self.staging_reader.read_payloads("stg_orion_accounts", run_id=run_id)

        insert_rows = _build_staff_rows(
            staff_identification=staff_identification,
            appendix_rows=appendix_rows,
            lotus_rows=lotus_rows,
            flexcube_users=flexcube_users,
            identity_rows=identity_rows,
            account_rows=account_rows,
        )

        self.db.execute("DELETE FROM staff")
        self.db.execute_many(
            """
            INSERT INTO staff (
                personnel_number,
                staff_name,
                first_name,
                last_name,
                id_card_number,
                national_id,
                user_code,
                flexcube_no,
                obpm_no,
                nt_username,
                identity_email,
                customer_code,
                account_number,
                department,
                department_name,
                section_name,
                sub_section,
                branch_posted,
                main_department,
                main_section,
                main_sub_section,
                primary_position,
                primary_position_description,
                primary_position_category,
                manager_name,
                manager_position,
                manager_email,
                location,
                departure_date,
                departure_details
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            insert_rows,
        )
        self.db.commit()

        return TransformResult(
            rows_read=(
                len(staff_identification)
                + len(appendix_rows)
                + len(lotus_rows)
                + len(flexcube_users)
                + len(identity_rows)
                + len(account_rows)
            ),
            rows_inserted=len(insert_rows),
            rows_updated=0,
            rows_rejected=0,
        )


def _build_staff_rows(
    staff_identification: list[dict[str, Any]],
    appendix_rows: list[dict[str, Any]],
    lotus_rows: list[dict[str, Any]],
    flexcube_users: list[dict[str, Any]],
    identity_rows: list[dict[str, Any]],
    account_rows: list[dict[str, Any]],
) -> list[list[Any]]:
    appendix_by_personnel = {_personnel_number(row): row for row in appendix_rows if _personnel_number(row)}
    lotus_by_staff_no = {_staff_no(row): row for row in lotus_rows if _staff_no(row)}
    flexcube_by_id = {_normalized(_get(row, ["id_card_number"])): row for row in flexcube_users}
    customer_by_identity = {
        _normalized(_get(row, ["identification_number"])): _get(row, ["customer_code"])
        for row in identity_rows
    }
    accounts_by_customer = _accounts_by_customer(account_rows)

    base_personnel_numbers = []
    base_rows: dict[Any, dict[str, Any]] = {}
    for row in staff_identification:
        personnel_number = _personnel_number(row)
        base_personnel_numbers.append(personnel_number)
        base_rows[personnel_number] = row
    for row in appendix_rows:
        personnel_number = _personnel_number(row)
        if personnel_number not in base_rows:
            base_personnel_numbers.append(personnel_number)
            base_rows[personnel_number] = {}

    insert_rows = []
    seen = set()
    for personnel_number in base_personnel_numbers:
        staff_row = base_rows.get(personnel_number, {})
        appendix_row = appendix_by_personnel.get(personnel_number, {})
        lotus_row = lotus_by_staff_no.get(personnel_number, {})

        id_card_number = _first_value(
                    _get(staff_row, ["Identification Number", "identification_number"]),
            _get(appendix_row, ["ID Number", "id_number"]),
            _get(lotus_row, ["Flexcube No", "flexcube_no"]),
        )
        flexcube_user = flexcube_by_id.get(_normalized(id_card_number), {})
        user_code = _first_value(
            _get(flexcube_user, ["user_code"]),
            _get(lotus_row, ["Flexcube No", "flexcube_no"]),
            _get(staff_row, ["nt_username"]),
            _get(appendix_row, ["BOVNT_Custom", "bovnt_custom"]),
        )
        customer_code = customer_by_identity.get(_normalized(id_card_number))
        account_numbers = accounts_by_customer.get(customer_code) or [None]

        for account_number in account_numbers:
            dedupe_key = (user_code, customer_code, account_number, id_card_number)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            insert_rows.append(
                [
                    personnel_number,
                    _first_value(
                        _get(staff_row, ["Name", "name"]),
                        _get(staff_row, ["full_name"]),
                        _get(appendix_row, ["Full Name", "full_name"]),
                    ),
                    _first_value(
                        _get(staff_row, ["first_name"]),
                        _get(appendix_row, ["FirstName", "first_name"]),
                    ),
                    _first_value(
                        _get(staff_row, ["last_name"]),
                        _get(appendix_row, ["LastName", "last_name"]),
                    ),
                    id_card_number,
                    id_card_number,
                    user_code,
                    _get(lotus_row, ["Flexcube No", "flexcube_no"]),
                    _get(lotus_row, ["OBPM No", "obpm_no"]),
                    _first_value(
                        _get(flexcube_user, ["nt_username"]),
                        _get(staff_row, ["nt_username"]),
                        _get(appendix_row, ["BOVNT_Custom", "bovnt_custom"]),
                    ),
                    _first_value(
                        _get(staff_row, ["email"]),
                        _get(appendix_row, ["IdentityEmail", "identity_email"]),
                    ),
                    customer_code,
                    account_number,
                    _get(staff_row, ["Department", "department"]),
                    _first_value(
                        _get(staff_row, ["department"]),
                        _get(appendix_row, ["Department Name", "department_name"]),
                    ),
                    _first_value(
                        _get(staff_row, ["section"]),
                        _get(appendix_row, ["Section Name", "section_name"]),
                    ),
                    _first_value(
                        _get(staff_row, ["subsection", "sub_section"]),
                        _get(appendix_row, ["Sub-section", "sub_section"]),
                    ),
                    _get(appendix_row, ["Branch Posted", "branch_posted"]),
                    _get(appendix_row, ["Main Department", "main_department"]),
                    _get(appendix_row, ["Main Section", "main_section"]),
                    _get(appendix_row, ["Main Sub-section", "main_sub_section"]),
                    _first_value(
                        _get(staff_row, ["position_id"]),
                        _get(appendix_row, ["Primary Position", "primary_position"]),
                    ),
                    _first_value(
                        _get(staff_row, ["position_description"]),
                        _get(appendix_row, ["Primary Position Description", "primary_position_description"]),
                        _get(staff_row, ["Primary Position Description", "primary_position_description"]),
                    ),
                    _first_value(
                        _get(staff_row, ["position_type"]),
                        _get(appendix_row, ["Primary Position Category", "primary_position_category"]),
                        _get(staff_row, ["Primary Position Category", "primary_position_category"]),
                    ),
                    _first_value(
                        _get(staff_row, ["manager_name"]),
                        _get(appendix_row, ["Manager Name", "manager_name"]),
                    ),
                    _first_value(
                        _get(staff_row, ["parent_position_description"]),
                        _get(appendix_row, ["Manager Position", "manager_position"]),
                    ),
                    _first_value(
                        _get(staff_row, ["manager_email"]),
                        _get(appendix_row, ["Manager Email", "manager_email"]),
                    ),
                    _get(lotus_row, ["Location", "location"]),
                    _get(staff_row, ["employment_end_date"]),
                    _get(staff_row, ["worker_status"]),
                ]
            )

    return insert_rows


def _accounts_by_customer(account_rows: list[dict[str, Any]]) -> dict[Any, list[Any]]:
    accounts_by_customer: dict[Any, list[Any]] = {}
    for row in account_rows:
        customer_code = _get(row, ["customer_code"])
        account_number = _get(row, ["account_number"])
        if customer_code is None:
            continue
        accounts_by_customer.setdefault(customer_code, []).append(account_number)
    return accounts_by_customer


def _personnel_number(row: dict[str, Any]) -> Any:
    return _get(
        row,
        [
            "Personnel Number",
            "personnel_number",
            "PersonnelNumber",
            "personnelnumber",
            "worker_personnel_number",
        ],
    )


def _staff_no(row: dict[str, Any]) -> Any:
    return _get(row, ["Staff No", "staff_no"])


def _get(row: dict[str, Any], keys: list[str]) -> Any:
    normalized = {_normalized(key): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(_normalized(key))
        if value not in (None, ""):
            return value
    return None


def _normalized(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def _first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None

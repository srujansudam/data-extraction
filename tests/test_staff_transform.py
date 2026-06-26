from __future__ import annotations

from pathlib import Path

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.staging.writer import StagingWriter
from data_extraction.tracking.runs import ExtractionRunTracker
from data_extraction.transform.staff import StaffTransformJob


def create_test_run(db: SQLiteAdapter) -> int:
    return ExtractionRunTracker(db).start_run(
        run_type="daily",
        window_start="2026-05-25T00:00:00+02:00",
        window_end="2026-05-26T00:00:00+02:00",
        triggered_by="manual",
    )


def stage_staff_inputs(db: SQLiteAdapter, run_id: int) -> None:
    writer = StagingWriter(db)
    writer.write_rows(
        "stg_hris_consolidated",
        run_id,
        "hris",
        "hris_consolidated",
        [
            {
                "worker_personnel_number": "P001",
                "full_name": "Alice Staff",
                "first_name": "Alice",
                "last_name": "Staff",
                "identification_number": "ID001",
                "department": "Internal Audit",
                "section": "Reviews",
                "subsection": "Banking",
                "position_id": "AUD",
                "position_description": "Senior Auditor",
                "position_type": "Professional",
                "manager_name": "Manager One",
                "parent_position_description": "Head",
                "manager_email": "manager@example.test",
                "email": "alice@example.test",
                "nt_username": "alice.nt",
            },
            {
                "worker_personnel_number": "P002",
                "full_name": "Bob No Account",
                "identification_number": "ID002",
                "department": "Risk",
            },
        ],
    )
    writer.write_rows(
        "stg_lotus_bov_employees",
        run_id,
        "lotus_notes",
        "LN - BOV Employees",
        [
            {
                "Staff No": "P001",
                "User Name": "Alice Staff",
                "OBPM No": "OBPM1",
                "Flexcube No": "U001",
                "Location": "Valletta",
            }
        ],
    )
    writer.write_rows(
        "stg_flexcube_user_details",
        run_id,
        "flexcube",
        "FCBOV.SMTB_USER",
        [{"user_code": "U001", "nt_username": "alice.nt", "id_card_number": "ID001"}],
    )
    writer.write_rows(
        "stg_orion_customer_identity_lookup",
        run_id,
        "orion",
        "ORION.EOM_CUSTOMER",
        [{"identification_number": "ID001", "customer_code": "C001"}],
    )
    writer.write_rows(
        "stg_orion_accounts",
        run_id,
        "orion",
        "ORION.ACCOUNT",
        [
            {"customer_code": "C001", "account_number": "ACC001"},
            {"customer_code": "C001", "account_number": "ACC002"},
        ],
    )


def test_staff_transform_merges_sources_and_expands_accounts(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        stage_staff_inputs(db, run_id)

        result = StaffTransformJob(db, StagingReader(db)).run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all(
            """
            SELECT personnel_number, staff_name, first_name, last_name, id_card_number,
                   user_code, customer_code, account_number, location, nt_username
            FROM staff
            ORDER BY personnel_number, account_number
            """
        )

        assert result.rows_inserted == 3
        assert rows == [
            {
                "personnel_number": "P001",
                "staff_name": "Alice Staff",
                "first_name": "Alice",
                "last_name": "Staff",
                "id_card_number": "ID001",
                "user_code": "U001",
                "customer_code": "C001",
                "account_number": "ACC001",
                "location": "Valletta",
                "nt_username": "alice.nt",
            },
            {
                "personnel_number": "P001",
                "staff_name": "Alice Staff",
                "first_name": "Alice",
                "last_name": "Staff",
                "id_card_number": "ID001",
                "user_code": "U001",
                "customer_code": "C001",
                "account_number": "ACC002",
                "location": "Valletta",
                "nt_username": "alice.nt",
            },
            {
                "personnel_number": "P002",
                "staff_name": "Bob No Account",
                "first_name": None,
                "last_name": None,
                "id_card_number": "ID002",
                "user_code": None,
                "customer_code": None,
                "account_number": None,
                "location": None,
                "nt_username": None,
            },
        ]
    finally:
        db.close()


def test_staff_transform_refreshes_final_table_on_rerun(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        first_run_id = create_test_run(db)
        stage_staff_inputs(db, first_run_id)
        job = StaffTransformJob(db, StagingReader(db))
        job.run(first_run_id, None, None)

        second_run_id = create_test_run(db)
        StagingWriter(db).write_rows(
            "stg_hris_consolidated",
            second_run_id,
            "hris",
            "hris_consolidated",
            [{"worker_personnel_number": "P003", "full_name": "Fresh Staff"}],
        )
        job.run(second_run_id, None, None)

        rows = db.query_all("SELECT personnel_number, staff_name FROM staff")

        assert rows == [{"personnel_number": "P003", "staff_name": "Fresh Staff"}]
    finally:
        db.close()

from __future__ import annotations

from pathlib import Path

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.tracking.runs import ExtractionRunTracker
from data_extraction.transform.users import UsersTransformJob


def create_test_run(db: SQLiteAdapter) -> int:
    return ExtractionRunTracker(db).start_run(
        run_type="daily",
        window_start=None,
        window_end=None,
        triggered_by="manual",
    )


def insert_staff_row(
    db: SQLiteAdapter,
    user_code: str,
    customer_code: str | None,
    account_number: str | None,
    id_card_number: str | None = "ID001",
    location: str | None = "Valletta",
    departure_date: str | None = None,
    departure_details: str | None = None,
) -> None:
    db.execute(
        """
        INSERT INTO staff (
            user_code,
            customer_code,
            id_card_number,
            account_number,
            location,
            departure_date,
            departure_details
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            user_code,
            customer_code,
            id_card_number,
            account_number,
            location,
            departure_date,
            departure_details,
        ],
    )


def test_users_transform_projects_staff_rows_and_dedupes(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        insert_staff_row(db, "U001", "C002", "ACC002", id_card_number=None, location=None)
        insert_staff_row(db, "U001", "C001", "ACC001", id_card_number=None, location=None)
        insert_staff_row(
            db,
            "U001",
            "C001",
            "ACC002",
            departure_date="2026-01-31",
            departure_details="Retired",
        )
        insert_staff_row(db, "U001", "C001", "ACC001", id_card_number=None, location=None)
        db.commit()

        result = UsersTransformJob(db).run(run_id, None, None)

        rows = db.query_all(
            """
            SELECT user_code, customer_code, id_card_number, account_number,
                   departure_date, departure_details, location
            FROM users
            ORDER BY account_number
            """
        )

        assert result.rows_read == 4
        assert result.rows_inserted == 1
        assert rows == [
            {
                "user_code": "U001",
                "customer_code": "C001",
                "id_card_number": "ID001",
                "account_number": "ACC001",
                "departure_date": "2026-01-31",
                "departure_details": "Retired",
                "location": "Valletta",
            },
        ]
        association_rows = db.query_all(
            """
            SELECT user_code, customer_code, account_number,
                   source_system, source_run_id
            FROM user_customer_account_association
            ORDER BY customer_code, account_number
            """
        )
        assert association_rows == [
            {
                "user_code": "U001",
                "customer_code": "C001",
                "account_number": "ACC001",
                "source_system": "internal",
                "source_run_id": str(run_id),
            },
            {
                "user_code": "U001",
                "customer_code": "C001",
                "account_number": "ACC002",
                "source_system": "internal",
                "source_run_id": str(run_id),
            },
            {
                "user_code": "U001",
                "customer_code": "C002",
                "account_number": "ACC002",
                "source_system": "internal",
                "source_run_id": str(run_id),
            },
        ]
    finally:
        db.close()


def test_users_transform_refreshes_final_table_on_rerun(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        first_run_id = create_test_run(db)
        insert_staff_row(db, "U001", "C001", "ACC001")
        db.commit()
        job = UsersTransformJob(db)
        job.run(first_run_id, None, None)

        db.execute("DELETE FROM staff")
        insert_staff_row(db, "U002", "C002", "ACC002", id_card_number="ID002")
        db.commit()
        second_run_id = create_test_run(db)
        job.run(second_run_id, None, None)

        rows = db.query_all("SELECT user_code, customer_code, account_number FROM users")
        association_rows = db.query_all(
            """
            SELECT user_code, customer_code, account_number
            FROM user_customer_account_association
            """
        )

        assert rows == [{"user_code": "U002", "customer_code": "C002", "account_number": "ACC002"}]
        assert association_rows == [
            {"user_code": "U002", "customer_code": "C002", "account_number": "ACC002"}
        ]
    finally:
        db.close()

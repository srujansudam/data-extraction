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
    customer_code: str,
    account_number: str,
    id_card_number: str = "ID001",
    location: str = "Valletta",
) -> None:
    db.execute(
        """
        INSERT INTO staff (
            user_code,
            customer_code,
            id_card_number,
            account_number,
            location
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        [user_code, customer_code, id_card_number, account_number, location],
    )


def test_users_transform_projects_staff_rows_and_dedupes(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        insert_staff_row(db, "U001", "C001", "ACC001")
        insert_staff_row(db, "U001", "C001", "ACC002")
        insert_staff_row(db, "U001", "C001", "ACC001")
        db.commit()

        result = UsersTransformJob(db).run(run_id, None, None)

        rows = db.query_all(
            """
            SELECT user_code, customer_code, id_card_number, account_number, location
            FROM users
            ORDER BY account_number
            """
        )

        assert result.rows_read == 3
        assert result.rows_inserted == 2
        assert rows == [
            {
                "user_code": "U001",
                "customer_code": "C001",
                "id_card_number": "ID001",
                "account_number": "ACC001",
                "location": "Valletta",
            },
            {
                "user_code": "U001",
                "customer_code": "C001",
                "id_card_number": "ID001",
                "account_number": "ACC002",
                "location": "Valletta",
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

        assert rows == [{"user_code": "U002", "customer_code": "C002", "account_number": "ACC002"}]
    finally:
        db.close()

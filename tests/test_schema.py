import sqlite3
from pathlib import Path

import pytest

from data_extraction.db.schema import (
    STAGING_TABLE_NAMES,
    create_all_tables,
    create_staging_tables,
    create_tracking_tables,
)
from data_extraction.db.sqlite_adapter import SQLiteAdapter


TRACKING_TABLE_NAMES = {
    "extraction_run",
    "extraction_job_run",
    "extraction_job_watermark",
    "extraction_error_log",
    "source_file_ingestion",
    "data_quality_check",
}

MODEL_TABLE_NAMES = {
    "account_data",
    "account_customer_association",
    "dormant_account",
    "customer_data",
    "third_party_access",
    "allowed_third_party",
    "related_parties",
    "transaction_data",
    "users",
    "user_customer_account_association",
    "staff",
    "credit_cards",
    "exchange_rate",
    "enquiry",
    "eom_book_balance",
    "office_accounts",
    "legal_rulings",
    "loans",
}

WORKFLOW_TABLE_NAMES = {
    "scenario",
    "triggers",
    "trigger_transaction_association",
    "trigger_user_association",
    "trigger_change_log",
    "logs",
}


def get_table_names(db: SQLiteAdapter) -> set[str]:
    rows = db.query_all(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    )
    return {row["name"] for row in rows}


def test_create_tracking_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)

        table_names = get_table_names(db)

        assert TRACKING_TABLE_NAMES.issubset(table_names)
    finally:
        db.close()


def test_create_all_tables_includes_model_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)

        table_names = get_table_names(db)

        assert MODEL_TABLE_NAMES.issubset(table_names)
    finally:
        db.close()


def test_create_staging_tables_creates_expected_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_staging_tables(db)

        table_names = get_table_names(db)

        assert set(STAGING_TABLE_NAMES).issubset(table_names)
    finally:
        db.close()


def test_create_staging_tables_includes_multisource_lookup_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_staging_tables(db)

        table_names = get_table_names(db)

        assert "stg_flexcube_deceased_customers" in table_names
        assert "stg_orion_customer_links" in table_names
        assert "stg_flexcube_user_details" in table_names
        assert "stg_orion_customer_identity_lookup" in table_names
    finally:
        db.close()


def test_create_all_tables_includes_staging_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)

        table_names = get_table_names(db)

        assert set(STAGING_TABLE_NAMES).issubset(table_names)
    finally:
        db.close()


def test_create_all_tables_includes_full_application_schema(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        create_all_tables(db)

        expected_tables = (
            TRACKING_TABLE_NAMES
            | MODEL_TABLE_NAMES
            | WORKFLOW_TABLE_NAMES
            | set(STAGING_TABLE_NAMES)
        )

        assert expected_tables.issubset(get_table_names(db))
    finally:
        db.close()


def test_workflow_tables_preserve_required_fields_and_checks(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)

        trigger_user_columns = {
            row["name"] for row in db.query_all("PRAGMA table_info(trigger_user_association)")
        }
        change_log_columns = {
            row["name"] for row in db.query_all("PRAGMA table_info(trigger_change_log)")
        }
        log_columns = {row["name"] for row in db.query_all("PRAGMA table_info(logs)")}
        triggers_sql = db.query_one(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'triggers'"
        )

        assert "reason" in trigger_user_columns
        assert "changes" in change_log_columns
        assert "username" in log_columns
        assert triggers_sql is not None
        assert triggers_sql["sql"].upper().count("CHECK") == 3
    finally:
        db.close()


def test_relationship_tables_have_required_columns_and_indexes(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)

        account_columns = {
            row["name"] for row in db.query_all("PRAGMA table_info(account_customer_association)")
        }
        user_columns = {
            row["name"]
            for row in db.query_all("PRAGMA table_info(user_customer_account_association)")
        }
        index_names = {
            row["name"]
            for row in db.query_all(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'index'
                """
            )
        }

        assert account_columns == {
            "id",
            "account_number",
            "customer_code",
            "relationship_type",
            "source_system",
            "source_run_id",
            "extracted_at",
        }
        assert user_columns == {
            "id",
            "user_code",
            "customer_code",
            "account_number",
            "source_system",
            "source_run_id",
            "extracted_at",
        }
        assert {
            "ix_account_customer_association_account",
            "ix_account_customer_association_customer",
            "ix_user_customer_account_association_user",
            "ix_user_customer_account_association_customer",
            "ix_user_customer_account_association_account",
        }.issubset(index_names)
    finally:
        db.close()


def test_staging_tables_have_standard_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_staging_tables(db)

        rows = db.query_all("PRAGMA table_info(stg_flexcube_office_accounts)")
        columns = {row["name"]: row for row in rows}

        assert list(columns) == [
            "staging_id",
            "run_id",
            "source_system",
            "source_object",
            "source_row_hash",
            "source_payload",
            "extracted_at",
        ]
        assert columns["staging_id"]["pk"] == 1
        assert columns["source_system"]["notnull"] == 1
        assert columns["source_object"]["notnull"] == 1
        assert columns["source_payload"]["notnull"] == 1
        assert columns["extracted_at"]["dflt_value"] == "CURRENT_TIMESTAMP"
    finally:
        db.close()


@pytest.mark.parametrize(
    ("table_name", "columns", "values"),
    [
        ("account_data", "account_number", ["ACC1"]),
        (
            "account_customer_association",
            "account_number, customer_code",
            ["ACC1", "CUST1"],
        ),
        ("customer_data", "customer_code", ["CUST1"]),
        ("users", "user_code", ["USER1"]),
        (
            "user_customer_account_association",
            "user_code, customer_code, account_number",
            ["USER1", "CUST1", "ACC1"],
        ),
        ("credit_cards", "transaction_reference", ["TX1"]),
        ("loans", "account_number", ["ACC1"]),
        ("scenario", "scenario_encoded", ["SCENARIO_1"]),
        (
            "third_party_access",
            "customer_code, account_code",
            ["CUST1", "ACC1"],
        ),
        (
            "allowed_third_party",
            "customer_code, account_code",
            ["CUST1", "ACC1"],
        ),
        (
            "enquiry",
            "user_code, function_id, start_time, terminal_id, action",
            ["USER1", "FUNC1", "2026-05-25 10:00:00", "TERM1", "EXECUTEQUERY"],
        ),
        (
            "eom_book_balance",
            "eom_date, account_number",
            ["2026-05-31", "ACC1"],
        ),
    ],
)
def test_required_model_unique_constraints(
    tmp_path: Path,
    table_name: str,
    columns: str,
    values: list[str],
) -> None:
    db = SQLiteAdapter(str(tmp_path / f"{table_name}.db"))
    db.connect()

    try:
        create_all_tables(db)
        placeholders = ", ".join("?" for _ in values)
        insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        db.execute(insert_sql, values)
        db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(insert_sql, values)
    finally:
        db.close()


def test_required_workflow_association_unique_constraints(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        db.execute(
            "INSERT INTO scenario (scenario_encoded) VALUES (?)",
            ["SCENARIO_1"],
        )
        db.execute(
            "INSERT INTO triggers (scenario_id, status) VALUES (?, ?)",
            [1, "NEW"],
        )
        db.execute(
            """
            INSERT INTO trigger_transaction_association (trigger_id, transaction_id)
            VALUES (?, ?)
            """,
            [1, "TX1"],
        )
        db.execute(
            """
            INSERT INTO trigger_user_association (trigger_id, user_id, reason)
            VALUES (?, ?, ?)
            """,
            [1, "USER1", "review"],
        )
        db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """
                INSERT INTO trigger_transaction_association (trigger_id, transaction_id)
                VALUES (?, ?)
                """,
                [1, "TX1"],
            )
        db.rollback()

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """
                INSERT INTO trigger_user_association (trigger_id, user_id)
                VALUES (?, ?)
                """,
                [1, "USER1"],
            )
    finally:
        db.close()


def test_office_accounts_has_office_account_name(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)

        rows = db.query_all("PRAGMA table_info(office_accounts)")
        column_names = {row["name"] for row in rows}

        assert "office_account_name" in column_names
    finally:
        db.close()


def test_staff_table_has_core_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)

        rows = db.query_all("PRAGMA table_info(staff)")
        column_names = {row["name"] for row in rows}

        assert "personnel_number" in column_names
        assert "user_code" in column_names
        assert "customer_code" in column_names
        assert "account_number" in column_names
        assert "location" in column_names
        assert "departure_date" in column_names
        assert "departure_details" in column_names
    finally:
        db.close()


def test_can_insert_extraction_run(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_tracking_tables(db)

        db.execute(
            """
            INSERT INTO extraction_run (
                run_type,
                status,
                window_start,
                window_end,
                triggered_by,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                "daily",
                "running",
                "2026-05-25T00:00:00+02:00",
                "2026-05-26T00:00:00+02:00",
                "manual",
                "test run",
            ],
        )
        db.commit()

        row = db.query_one("SELECT run_type, status FROM extraction_run WHERE run_id = ?", [1])

        assert row == {"run_type": "daily", "status": "running"}
    finally:
        db.close()

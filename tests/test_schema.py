from pathlib import Path

from data_extraction.db.schema import (
    STAGING_TABLE_NAMES,
    create_all_tables,
    create_staging_tables,
    create_tracking_tables,
)
from data_extraction.db.sqlite_adapter import SQLiteAdapter


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

        assert "extraction_run" in table_names
        assert "extraction_job_run" in table_names
        assert "extraction_job_watermark" in table_names
        assert "extraction_error_log" in table_names
        assert "source_file_ingestion" in table_names
        assert "data_quality_check" in table_names
    finally:
        db.close()


def test_create_all_tables_includes_model_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)

        table_names = get_table_names(db)

        assert "account_data" in table_names
        assert "dormant_account" in table_names
        assert "customer_data" in table_names
        assert "third_party_access" in table_names
        assert "allowed_third_party" in table_names
        assert "related_parties" in table_names
        assert "transaction_data" in table_names
        assert "users" in table_names
        assert "staff" in table_names
        assert "credit_cards" in table_names
        assert "exchange_rate" in table_names
        assert "enquiry" in table_names
        assert "eom_book_balance" in table_names
        assert "office_accounts" in table_names
        assert "legal_rulings" in table_names
        assert "loans" in table_names
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

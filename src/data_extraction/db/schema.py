from __future__ import annotations

from data_extraction.db.adapter import DatabaseAdapter


TRACKING_TABLE_SQL = [
    """
    CREATE TABLE IF NOT EXISTS extraction_run (
        run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_type TEXT NOT NULL,
        status TEXT NOT NULL,
        window_start TEXT,
        window_end TEXT,
        started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        triggered_by TEXT NOT NULL DEFAULT 'scheduler',
        notes TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS extraction_job_run (
        job_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL,
        job_name TEXT NOT NULL,
        source_system TEXT NOT NULL,
        target_table TEXT NOT NULL,
        status TEXT NOT NULL,
        window_start TEXT,
        window_end TEXT,
        rows_extracted INTEGER NOT NULL DEFAULT 0,
        rows_inserted INTEGER NOT NULL DEFAULT 0,
        rows_updated INTEGER NOT NULL DEFAULT 0,
        rows_rejected INTEGER NOT NULL DEFAULT 0,
        started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        error_message TEXT,
        FOREIGN KEY (run_id) REFERENCES extraction_run(run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS extraction_job_watermark (
        job_name TEXT PRIMARY KEY,
        source_system TEXT NOT NULL,
        target_table TEXT NOT NULL,
        last_successful_window_start TEXT,
        last_successful_window_end TEXT,
        last_successful_run_id INTEGER,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS extraction_error_log (
        error_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        job_run_id INTEGER,
        job_name TEXT,
        source_system TEXT,
        error_type TEXT NOT NULL,
        error_message TEXT NOT NULL,
        error_detail TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (run_id) REFERENCES extraction_run(run_id),
        FOREIGN KEY (job_run_id) REFERENCES extraction_job_run(job_run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS source_file_ingestion (
        file_ingestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        source_system TEXT NOT NULL,
        source_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_hash TEXT,
        status TEXT NOT NULL,
        rows_read INTEGER NOT NULL DEFAULT 0,
        rows_loaded INTEGER NOT NULL DEFAULT 0,
        ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        error_message TEXT,
        FOREIGN KEY (run_id) REFERENCES extraction_run(run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS data_quality_check (
        check_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        job_run_id INTEGER,
        table_name TEXT NOT NULL,
        check_name TEXT NOT NULL,
        check_status TEXT NOT NULL,
        expected_value TEXT,
        actual_value TEXT,
        details TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (run_id) REFERENCES extraction_run(run_id),
        FOREIGN KEY (job_run_id) REFERENCES extraction_job_run(job_run_id)
    )
    """,
]


MODEL_TABLE_SQL = [
    """
    CREATE TABLE IF NOT EXISTS account_data (
        account_number TEXT,
        account_currency TEXT,
        acc_designation TEXT,
        customer_code TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dormant_account (
        account_number TEXT,
        date TEXT,
        dormant TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS customer_data (
        customer_code TEXT,
        phone_number TEXT,
        creation_date TEXT,
        identification_number TEXT,
        customer_name TEXT,
        customer_address TEXT,
        age INTEGER,
        deceased_date TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS third_party_access (
        customer_code TEXT,
        account_code TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS allowed_third_party (
        customer_code TEXT,
        account_code TEXT,
        reason TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS related_parties (
        user_code TEXT,
        customer_code TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transaction_data (
        transaction_serial_number TEXT,
        first_loan_drawdown_date TEXT,
        transaction_reference TEXT,
        channel_lvl_4 TEXT,
        transaction_date_time TEXT,
        cheque_number TEXT,
        detailed_statement_description TEXT,
        user_code TEXT,
        amount REAL,
        transaction_code_description TEXT,
        transaction_product_description TEXT,
        account_number TEXT,
        initiator_id TEXT,
        statement_description TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        user_code TEXT,
        customer_code TEXT,
        id_card_number TEXT,
        account_number TEXT,
        departure_date TEXT,
        departure_details TEXT,
        location TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS staff (
        personnel_number TEXT,
        staff_name TEXT,
        first_name TEXT,
        last_name TEXT,
        id_card_number TEXT,
        national_id TEXT,
        user_code TEXT,
        flexcube_no TEXT,
        obpm_no TEXT,
        nt_username TEXT,
        identity_email TEXT,
        customer_code TEXT,
        account_number TEXT,
        department TEXT,
        department_name TEXT,
        section_name TEXT,
        sub_section TEXT,
        branch_posted TEXT,
        main_department TEXT,
        main_section TEXT,
        main_sub_section TEXT,
        primary_position TEXT,
        primary_position_description TEXT,
        primary_position_category TEXT,
        manager_name TEXT,
        manager_position TEXT,
        manager_email TEXT,
        location TEXT,
        departure_date TEXT,
        departure_details TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS credit_cards (
        transaction_reference TEXT,
        user_code TEXT,
        date TEXT,
        customer_code TEXT,
        branch_code TEXT,
        amount REAL,
        credit_card_number TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS exchange_rate (
        transaction_id TEXT,
        customer_code TEXT,
        base_currency TEXT,
        transaction_type TEXT,
        branch TEXT,
        amount REAL,
        transaction_currency TEXT,
        exchange_rate REAL,
        middle_rate REAL,
        transaction_date TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS enquiry (
        user_code TEXT,
        function_id TEXT,
        start_time TEXT,
        action_time TEXT,
        terminal_id TEXT,
        branch_code TEXT,
        description TEXT,
        action TEXT,
        pkvals TEXT,
        breadcrumbs TEXT,
        error_msg TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS eom_book_balance (
        eom_date TEXT,
        customer_code TEXT,
        account_number TEXT,
        product_lvl_7 TEXT,
        book_balance REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS office_accounts (
        office_account_number TEXT,
        customer_code TEXT,
        office_account_name TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS legal_rulings (
        deceased_customer_code TEXT,
        deceased_account_number TEXT,
        ruling_holder_ID TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS loans (
        account_number TEXT,
        customer_code TEXT,
        product_lvl_6 TEXT,
        product_lvl_7 TEXT,
        drawdown_expiry_date TEXT
    )
    """,
]


STAGING_TABLE_NAMES = [
    "stg_orion_accounts",
    "stg_orion_customers",
    "stg_orion_transactions",
    "stg_orion_loans",
    "stg_orion_eom_book_balance",
    "stg_orion_adc_access",
    "stg_orion_customer_links",
    "stg_orion_customer_identity_lookup",
    "stg_flexcube_dormant_accounts",
    "stg_flexcube_office_accounts",
    "stg_flexcube_credit_cards",
    "stg_flexcube_exchange_rate",
    "stg_flexcube_enquiry",
    "stg_flexcube_deceased_customers",
    "stg_flexcube_user_details",
    "stg_hris_staff_identification",
    "stg_hris_personnel_contact_detail",
    "stg_hris_appendix_3_crm",
    "stg_lotus_bov_employees",
    "stg_lotus_legal_rulings",
    "stg_lotus_garnishee_orders",
    "stg_lotus_poa_revocation",
    "stg_lotus_discrepancies_management",
]


def _staging_table_sql(table_name: str) -> str:
    return f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        staging_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        source_system TEXT NOT NULL,
        source_object TEXT NOT NULL,
        source_row_hash TEXT,
        source_payload TEXT NOT NULL,
        extracted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """


def create_tracking_tables(db: DatabaseAdapter) -> None:
    for sql in TRACKING_TABLE_SQL:
        db.execute(sql)

    db.commit()


def create_model_tables(db: DatabaseAdapter) -> None:
    for sql in MODEL_TABLE_SQL:
        db.execute(sql)

    db.commit()


def create_staging_tables(db: DatabaseAdapter) -> None:
    for table_name in STAGING_TABLE_NAMES:
        db.execute(_staging_table_sql(table_name))

    db.commit()


def create_all_tables(db: DatabaseAdapter) -> None:
    create_tracking_tables(db)
    create_model_tables(db)
    create_staging_tables(db)

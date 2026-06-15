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
    CREATE TABLE IF NOT EXISTS account_customer_association (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_number TEXT NOT NULL,
        customer_code TEXT NOT NULL,
        relationship_type TEXT,
        source_system TEXT,
        source_run_id TEXT,
        extracted_at DATETIME
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
    CREATE TABLE IF NOT EXISTS user_customer_account_association (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_code TEXT NOT NULL,
        customer_code TEXT,
        account_number TEXT,
        source_system TEXT,
        source_run_id TEXT,
        extracted_at DATETIME
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

WORKFLOW_TABLE_SQL = [
    """
    CREATE TABLE IF NOT EXISTS scenario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scenario_encoded TEXT NOT NULL,
        scenario_name TEXT,
        scenario_description TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS triggers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scenario_id INTEGER NOT NULL,
        trigger TEXT CHECK (
            trigger IS NULL OR UPPER(trigger) IN (
                'TRUE', 'FALSE', 'YES', 'NO', 'TRIGGERED', 'NOT_TRIGGERED',
                'TRANSACTION', 'USER', 'BOTH', 'AUTOMATED', 'MANUAL'
            )
        ),
        status TEXT CHECK (
            status IS NULL OR UPPER(status) IN (
                'NEW', 'PENDING', 'OPEN', 'IN_PROGRESS', 'IN PROGRESS',
                'REVIEWED', 'APPROVED', 'REJECTED', 'CLOSED', 'COMPLETED'
            )
        ),
        voucher_status TEXT CHECK (
            voucher_status IS NULL OR UPPER(voucher_status) IN (
                'PENDING', 'REQUESTED', 'RECEIVED', 'NOT_REQUESTED',
                'NOT REQUESTED', 'NOT_AVAILABLE', 'NOT AVAILABLE',
                'AVAILABLE', 'MISSING', 'REVIEWED'
            )
        ),
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT,
        FOREIGN KEY (scenario_id) REFERENCES scenario(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trigger_transaction_association (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trigger_id INTEGER NOT NULL,
        transaction_id TEXT NOT NULL,
        FOREIGN KEY (trigger_id) REFERENCES triggers(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trigger_user_association (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trigger_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        reason TEXT,
        FOREIGN KEY (trigger_id) REFERENCES triggers(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trigger_change_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trigger_id INTEGER NOT NULL,
        changed_by TEXT,
        changes TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trigger_id) REFERENCES triggers(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT,
        message TEXT NOT NULL,
        username TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS ix_extraction_job_run_run_id ON extraction_job_run(run_id)",
    "CREATE INDEX IF NOT EXISTS ix_extraction_error_log_run_id ON extraction_error_log(run_id)",
    "CREATE INDEX IF NOT EXISTS ix_source_file_ingestion_run_id ON source_file_ingestion(run_id)",
    "CREATE INDEX IF NOT EXISTS ix_data_quality_check_run_id ON data_quality_check(run_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_account_data_account_number "
    "ON account_data(account_number)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_account_customer_association "
    "ON account_customer_association(account_number, customer_code)",
    "CREATE INDEX IF NOT EXISTS ix_account_customer_association_account "
    "ON account_customer_association(account_number)",
    "CREATE INDEX IF NOT EXISTS ix_account_customer_association_customer "
    "ON account_customer_association(customer_code)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_customer_data_customer_code "
    "ON customer_data(customer_code)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_user_code ON users(user_code)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_user_customer_account_association "
    "ON user_customer_account_association(user_code, customer_code, account_number)",
    "CREATE INDEX IF NOT EXISTS ix_user_customer_account_association_user "
    "ON user_customer_account_association(user_code)",
    "CREATE INDEX IF NOT EXISTS ix_user_customer_account_association_customer "
    "ON user_customer_account_association(customer_code)",
    "CREATE INDEX IF NOT EXISTS ix_user_customer_account_association_account "
    "ON user_customer_account_association(account_number)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_credit_cards_transaction_reference "
    "ON credit_cards(transaction_reference)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_loans_account_number ON loans(account_number)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_scenario_scenario_encoded "
    "ON scenario(scenario_encoded)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_third_party_access_customer_account "
    "ON third_party_access(customer_code, account_code)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_allowed_third_party_customer_account "
    "ON allowed_third_party(customer_code, account_code)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_enquiry_business_key "
    "ON enquiry(user_code, function_id, start_time, terminal_id, action)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_eom_book_balance_eom_account "
    "ON eom_book_balance(eom_date, account_number)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_trigger_transaction "
    "ON trigger_transaction_association(trigger_id, transaction_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_trigger_user "
    "ON trigger_user_association(trigger_id, user_id)",
    "CREATE INDEX IF NOT EXISTS ix_scenario_name ON scenario(scenario_name)",
    "CREATE INDEX IF NOT EXISTS ix_triggers_scenario_id ON triggers(scenario_id)",
    "CREATE INDEX IF NOT EXISTS ix_triggers_status ON triggers(status)",
    "CREATE INDEX IF NOT EXISTS ix_triggers_voucher_status ON triggers(voucher_status)",
    "CREATE INDEX IF NOT EXISTS ix_trigger_transaction_transaction_id "
    "ON trigger_transaction_association(transaction_id)",
    "CREATE INDEX IF NOT EXISTS ix_trigger_user_user_id "
    "ON trigger_user_association(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_trigger_change_log_trigger_id "
    "ON trigger_change_log(trigger_id)",
    "CREATE INDEX IF NOT EXISTS ix_logs_username ON logs(username)",
    "CREATE INDEX IF NOT EXISTS ix_logs_created_at ON logs(created_at)",
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

    _ensure_column(db, "office_accounts", "office_account_name", "TEXT")
    db.commit()


def create_staging_tables(db: DatabaseAdapter) -> None:
    for table_name in STAGING_TABLE_NAMES:
        db.execute(_staging_table_sql(table_name))

    db.commit()


def create_workflow_tables(db: DatabaseAdapter) -> None:
    for sql in WORKFLOW_TABLE_SQL:
        db.execute(sql)

    db.commit()


def create_indexes(db: DatabaseAdapter) -> None:
    for sql in INDEX_SQL:
        db.execute(sql)

    db.commit()


def create_all_tables(db: DatabaseAdapter) -> None:
    create_tracking_tables(db)
    create_model_tables(db)
    create_staging_tables(db)
    create_workflow_tables(db)
    create_indexes(db)


def _ensure_column(
    db: DatabaseAdapter,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    columns = db.query_all(f"PRAGMA table_info({table_name})")
    if any(column["name"] == column_name for column in columns):
        return

    db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")

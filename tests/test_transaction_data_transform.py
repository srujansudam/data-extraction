from __future__ import annotations

from pathlib import Path

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.staging.writer import StagingWriter
from data_extraction.tracking.runs import ExtractionRunTracker
from data_extraction.transform.transaction_data import TransactionDataTransformJob


def create_test_run(db: SQLiteAdapter) -> int:
    run_tracker = ExtractionRunTracker(db)
    return run_tracker.start_run(
        run_type="daily",
        window_start="2026-05-25T00:00:00+02:00",
        window_end="2026-05-26T00:00:00+02:00",
        triggered_by="manual",
    )


def test_transaction_data_transform_loads_deduped_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        writer = StagingWriter(db)
        writer.write_rows(
            staging_table="stg_orion_transactions",
            run_id=run_id,
            source_system="orion",
            source_object="ORION.V_ACC_FINANCIAL_TRANSACTIONS",
            rows=[
                {
                    "transaction_serial_number": "TX001",
                    "first_loan_drawdown_date": "2025-01-01",
                    "transaction_reference": "REF001",
                    "channel_lvl_4": "Branch",
                    "transaction_date": "2026-05-25",
                    "transaction_time": "13:45",
                    "cheque_number": "CHQ001",
                    "detailed_statement_description": "Detailed",
                    "user_code": "USER1",
                    "amount": -100.0,
                    "transaction_code_description": "Withdrawal",
                    "transaction_product_description": "Current",
                    "account_number": "ACC001",
                },
                {
                    "transaction_serial_number": "TX001",
                    "transaction_reference": "DUPLICATE",
                    "transaction_date": "2026-05-25",
                    "transaction_time": "13:46",
                },
                {
                    "transaction_serial_number": "TX002",
                    "transaction_reference": "REF002",
                    "transaction_date": "2026-05-25",
                    "transaction_time": None,
                    "amount": 50.0,
                },
            ],
        )

        job = TransactionDataTransformJob(db=db, staging_reader=StagingReader(db))
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all(
            """
            SELECT transaction_serial_number, transaction_reference,
                   transaction_date_time, amount, initiator_id, statement_description
            FROM transaction_data
            ORDER BY transaction_serial_number
            """
        )

        assert result.rows_read == 3
        assert result.rows_inserted == 2
        assert rows == [
            {
                "transaction_serial_number": "TX001",
                "transaction_reference": "REF001",
                "transaction_date_time": "2026-05-25 13:45",
                "amount": -100.0,
                "initiator_id": None,
                "statement_description": None,
            },
            {
                "transaction_serial_number": "TX002",
                "transaction_reference": "REF002",
                "transaction_date_time": "2026-05-25",
                "amount": 50.0,
                "initiator_id": None,
                "statement_description": None,
            },
        ]
    finally:
        db.close()


def test_transaction_data_transform_replaces_incoming_serial_numbers(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        db.execute_many(
            """
            INSERT INTO transaction_data (
                transaction_serial_number,
                transaction_reference
            )
            VALUES (?, ?)
            """,
            [["TX001", "OLD"], ["KEEP", "KEEP"]],
        )
        db.commit()
        run_id = create_test_run(db)
        StagingWriter(db).write_rows(
            staging_table="stg_orion_transactions",
            run_id=run_id,
            source_system="orion",
            source_object="ORION.V_ACC_FINANCIAL_TRANSACTIONS",
            rows=[
                {
                    "transaction_serial_number": "TX001",
                    "transaction_reference": "NEW",
                    "transaction_date": "2026-05-25",
                }
            ],
        )

        job = TransactionDataTransformJob(db=db, staging_reader=StagingReader(db))
        job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all(
            """
            SELECT transaction_serial_number, transaction_reference
            FROM transaction_data
            ORDER BY transaction_serial_number
            """
        )

        assert rows == [
            {"transaction_serial_number": "KEEP", "transaction_reference": "KEEP"},
            {"transaction_serial_number": "TX001", "transaction_reference": "NEW"},
        ]
    finally:
        db.close()


def test_transaction_data_transform_empty_staging_succeeds(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        job = TransactionDataTransformJob(db=db, staging_reader=StagingReader(db))

        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        assert result.rows_read == 0
        assert result.rows_inserted == 0
        assert db.query_all("SELECT * FROM transaction_data") == []
    finally:
        db.close()

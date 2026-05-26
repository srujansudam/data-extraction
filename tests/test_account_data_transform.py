from __future__ import annotations

from pathlib import Path

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.staging.writer import StagingWriter
from data_extraction.tracking.runs import ExtractionRunTracker
from data_extraction.transform.account_data import AccountDataTransformJob


def create_test_run(db: SQLiteAdapter) -> int:
    run_tracker = ExtractionRunTracker(db)
    return run_tracker.start_run(
        run_type="daily",
        window_start="2026-05-25T00:00:00+02:00",
        window_end="2026-05-26T00:00:00+02:00",
        triggered_by="manual",
    )


def test_account_data_transform_loads_deduped_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        writer = StagingWriter(db)
        writer.write_rows(
            staging_table="stg_orion_accounts",
            run_id=run_id,
            source_system="orion",
            source_object="ORION.ACCOUNT",
            rows=[
                {
                    "account_number": "ACC001",
                    "account_currency": "Euro",
                    "acc_designation": "Current",
                    "customer_code": "C001",
                    "account_opening_date": "2025-01-01",
                },
                {
                    "account_number": "ACC001",
                    "account_currency": "Euro",
                    "acc_designation": "Current",
                    "customer_code": "C001",
                    "account_opening_date": "2025-01-01",
                },
                {
                    "account_number": "ACC001",
                    "account_currency": "Euro",
                    "acc_designation": "Current",
                    "customer_code": "C002",
                    "account_opening_date": "2025-01-01",
                },
            ],
        )

        job = AccountDataTransformJob(db=db, staging_reader=StagingReader(db))
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all(
            """
            SELECT account_number, account_currency, acc_designation, customer_code
            FROM account_data
            ORDER BY customer_code
            """
        )

        assert result.rows_read == 3
        assert result.rows_inserted == 2
        assert rows == [
            {
                "account_number": "ACC001",
                "account_currency": "Euro",
                "acc_designation": "Current",
                "customer_code": "C001",
            },
            {
                "account_number": "ACC001",
                "account_currency": "Euro",
                "acc_designation": "Current",
                "customer_code": "C002",
            },
        ]

        job_row = db.query_one(
            """
            SELECT status, rows_extracted, rows_inserted
            FROM extraction_job_run
            WHERE job_name = ?
            """,
            ["transform_account_data"],
        )

        assert job_row is not None
        assert job_row["status"] == "completed"
        assert job_row["rows_extracted"] == 3
        assert job_row["rows_inserted"] == 2
    finally:
        db.close()


def test_account_data_transform_uses_current_run_id_and_refreshes_table(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        writer = StagingWriter(db)
        old_run_id = create_test_run(db)
        writer.write_rows(
            staging_table="stg_orion_accounts",
            run_id=old_run_id,
            source_system="orion",
            source_object="ORION.ACCOUNT",
            rows=[{"account_number": "OLD", "customer_code": "OLD"}],
        )
        current_run_id = create_test_run(db)
        writer.write_rows(
            staging_table="stg_orion_accounts",
            run_id=current_run_id,
            source_system="orion",
            source_object="ORION.ACCOUNT",
            rows=[{"account_number": "NEW", "customer_code": "C001"}],
        )
        db.execute(
            """
            INSERT INTO account_data (
                account_number,
                account_currency,
                acc_designation,
                customer_code
            )
            VALUES (?, ?, ?, ?)
            """,
            ["STALE", None, None, "STALE"],
        )
        db.commit()

        job = AccountDataTransformJob(db=db, staging_reader=StagingReader(db))
        job.run(run_id=current_run_id, window_start=None, window_end=None)

        rows = db.query_all("SELECT account_number, customer_code FROM account_data")

        assert rows == [{"account_number": "NEW", "customer_code": "C001"}]
    finally:
        db.close()

from __future__ import annotations

from pathlib import Path

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.staging.writer import StagingWriter
from data_extraction.tracking.runs import ExtractionRunTracker
from data_extraction.transform.customer_data import CustomerDataTransformJob


def create_test_run(db: SQLiteAdapter) -> int:
    run_tracker = ExtractionRunTracker(db)
    return run_tracker.start_run(
        run_type="daily",
        window_start="2026-05-25T00:00:00+02:00",
        window_end="2026-05-26T00:00:00+02:00",
        triggered_by="manual",
    )


def stage_customer_inputs(db: SQLiteAdapter, run_id: int) -> None:
    writer = StagingWriter(db)
    writer.write_rows(
        staging_table="stg_orion_customers",
        run_id=run_id,
        source_system="orion",
        source_object="ORION.CUSTOMER",
        rows=[
            {
                "customer_code": "C001",
                "phone_number": "79000001",
                "identification_number": "ID001",
                "customer_name": "Customer One",
                "date_of_birth": "1990-05-27",
                "address_1": "Line 1",
                "address_2": "",
                "city": "Valletta",
                "country": "MT",
                "zip_code": "VLT 001",
            },
            {
                "customer_code": "C001",
                "phone_number": "DUPLICATE",
                "identification_number": "DUPLICATE",
                "customer_name": "Duplicate",
                "date_of_birth": "1990-05-27",
            },
            {
                "customer_code": "C002",
                "phone_number": "79000002",
                "identification_number": "ID002",
                "customer_name": "Customer Two",
                "date_of_birth": "not-a-date",
                "address_1": None,
                "address_2": "Second Line",
                "city": "",
                "country": "MT",
                "zip_code": None,
            },
        ],
    )
    writer.write_rows(
        staging_table="stg_orion_accounts",
        run_id=run_id,
        source_system="orion",
        source_object="ORION.ACCOUNT",
        rows=[
            {"customer_code": "C001", "account_opening_date": "2023-01-10"},
            {"customer_code": "C001", "account_opening_date": "2022-12-31"},
            {"customer_code": "C002", "account_opening_date": "2024-03-01"},
        ],
    )
    writer.write_rows(
        staging_table="stg_flexcube_deceased_customers",
        run_id=run_id,
        source_system="flexcube",
        source_object="FCBOV.sttms_cust_personal_ee_cu",
        rows=[{"customer_code": "C001", "deceased_date": "2026-01-01"}],
    )


def test_customer_data_transform_builds_customer_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        stage_customer_inputs(db, run_id)

        job = CustomerDataTransformJob(db=db, staging_reader=StagingReader(db))
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all(
            """
            SELECT customer_code, phone_number, creation_date, identification_number,
                   customer_name, customer_address, age, deceased_date
            FROM customer_data
            ORDER BY customer_code
            """
        )

        assert result.rows_read == 7
        assert result.rows_inserted == 2
        assert rows == [
            {
                "customer_code": "C001",
                "phone_number": "79000001",
                "creation_date": "2022-12-31",
                "identification_number": "ID001",
                "customer_name": "Customer One",
                "customer_address": "Line 1, Valletta, MT, VLT 001",
                "age": 35,
                "deceased_date": "2026-01-01",
            },
            {
                "customer_code": "C002",
                "phone_number": "79000002",
                "creation_date": "2024-03-01",
                "identification_number": "ID002",
                "customer_name": "Customer Two",
                "customer_address": "Second Line, MT",
                "age": None,
                "deceased_date": None,
            },
        ]

        job_row = db.query_one(
            """
            SELECT status, rows_extracted, rows_inserted
            FROM extraction_job_run
            WHERE job_name = ?
            """,
            ["transform_customer_data"],
        )

        assert job_row is not None
        assert job_row["status"] == "completed"
        assert job_row["rows_extracted"] == 7
        assert job_row["rows_inserted"] == 2
    finally:
        db.close()


def test_customer_data_transform_refreshes_final_table_on_rerun(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        stage_customer_inputs(db, run_id)
        job = CustomerDataTransformJob(db=db, staging_reader=StagingReader(db))
        job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        second_run_id = create_test_run(db)
        writer = StagingWriter(db)
        writer.write_rows(
            staging_table="stg_orion_customers",
            run_id=second_run_id,
            source_system="orion",
            source_object="ORION.CUSTOMER",
            rows=[
                {
                    "customer_code": "C003",
                    "phone_number": "79000003",
                    "identification_number": "ID003",
                    "customer_name": "Customer Three",
                    "date_of_birth": "2000-01-01",
                }
            ],
        )

        job.run(
            run_id=second_run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all("SELECT customer_code, customer_name FROM customer_data")

        assert rows == [{"customer_code": "C003", "customer_name": "Customer Three"}]
    finally:
        db.close()

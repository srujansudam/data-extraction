from __future__ import annotations

from pathlib import Path

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.staging.writer import StagingWriter
from data_extraction.tracking.runs import ExtractionRunTracker
from data_extraction.transform.legal_rulings import LegalRulingsTransformJob


def create_test_run(db: SQLiteAdapter) -> int:
    run_tracker = ExtractionRunTracker(db)
    return run_tracker.start_run(
        run_type="daily",
        window_start="2026-05-25T00:00:00+02:00",
        window_end="2026-05-26T00:00:00+02:00",
        triggered_by="manual",
    )


def test_legal_rulings_transform_matches_deceased_customer_accounts(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        writer = StagingWriter(db)
        writer.write_rows(
            staging_table="stg_lotus_legal_rulings",
            run_id=run_id,
            source_system="lotus_notes",
            source_object="LN - Succession & Legal rulings",
            rows=[
                {"Deceased Customer Code": "C001", "ID Card No": "ID001"},
                {"Deceased Customer Code": "C999", "ID Card No": "ID999"},
                {"deceased_customer_code": "C002", "id_card_no": "ID002"},
                {"Deceased Customer Code": "C001", "ID Card No": "ID001"},
            ],
        )
        writer.write_rows(
            staging_table="stg_orion_accounts",
            run_id=run_id,
            source_system="orion",
            source_object="ORION.ACCOUNT",
            rows=[
                {"customer_code": "C001", "account_number": "ACC001"},
                {"customer_code": "C001", "account_number": "ACC002"},
                {"customer_code": "C002", "account_number": "ACC003"},
            ],
        )

        job = LegalRulingsTransformJob(db=db, staging_reader=StagingReader(db))
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all(
            """
            SELECT deceased_customer_code, deceased_account_number, ruling_holder_ID
            FROM legal_rulings
            ORDER BY deceased_customer_code, deceased_account_number
            """
        )

        assert result.rows_read == 4
        assert result.rows_inserted == 3
        assert rows == [
            {
                "deceased_customer_code": "C001",
                "deceased_account_number": "ACC001",
                "ruling_holder_ID": "ID001",
            },
            {
                "deceased_customer_code": "C001",
                "deceased_account_number": "ACC002",
                "ruling_holder_ID": "ID001",
            },
            {
                "deceased_customer_code": "C002",
                "deceased_account_number": "ACC003",
                "ruling_holder_ID": "ID002",
            },
        ]
    finally:
        db.close()


def test_legal_rulings_transform_refreshes_final_table_on_rerun(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        first_run_id = create_test_run(db)
        writer = StagingWriter(db)
        writer.write_rows(
            staging_table="stg_lotus_legal_rulings",
            run_id=first_run_id,
            source_system="lotus_notes",
            source_object="LN - Succession & Legal rulings",
            rows=[{"Deceased Customer Code": "C001", "ID Card No": "ID001"}],
        )
        writer.write_rows(
            staging_table="stg_orion_accounts",
            run_id=first_run_id,
            source_system="orion",
            source_object="ORION.ACCOUNT",
            rows=[{"customer_code": "C001", "account_number": "ACC001"}],
        )
        job = LegalRulingsTransformJob(db=db, staging_reader=StagingReader(db))
        job.run(
            run_id=first_run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        second_run_id = create_test_run(db)
        writer.write_rows(
            staging_table="stg_lotus_legal_rulings",
            run_id=second_run_id,
            source_system="lotus_notes",
            source_object="LN - Succession & Legal rulings",
            rows=[{"Deceased Customer Code": "C002", "ID Card No / Ref No": "ID002"}],
        )
        writer.write_rows(
            staging_table="stg_orion_accounts",
            run_id=second_run_id,
            source_system="orion",
            source_object="ORION.ACCOUNT",
            rows=[{"customer_code": "C002", "account_number": "ACC002"}],
        )

        job.run(
            run_id=second_run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        rows = db.query_all(
            """
            SELECT deceased_customer_code, deceased_account_number, ruling_holder_ID
            FROM legal_rulings
            """
        )

        assert rows == [
            {
                "deceased_customer_code": "C002",
                "deceased_account_number": "ACC002",
                "ruling_holder_ID": "ID002",
            }
        ]
    finally:
        db.close()


def test_legal_rulings_transform_empty_lotus_staging_refreshes_to_empty(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        db.execute(
            """
            INSERT INTO legal_rulings (
                deceased_customer_code,
                deceased_account_number,
                ruling_holder_ID
            )
            VALUES (?, ?, ?)
            """,
            ["OLD", "OLD_ACC", "OLD_ID"],
        )
        db.commit()
        run_id = create_test_run(db)

        job = LegalRulingsTransformJob(db=db, staging_reader=StagingReader(db))
        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )

        assert result.rows_read == 0
        assert result.rows_inserted == 0
        assert db.query_all("SELECT * FROM legal_rulings") == []
    finally:
        db.close()

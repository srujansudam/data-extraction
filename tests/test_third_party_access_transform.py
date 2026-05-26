from __future__ import annotations

from pathlib import Path

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.staging.writer import StagingWriter
from data_extraction.tracking.runs import ExtractionRunTracker
from data_extraction.transform.third_party_access import ThirdPartyAccessTransformJob


def create_test_run(db: SQLiteAdapter) -> int:
    return ExtractionRunTracker(db).start_run(
        run_type="daily",
        window_start=None,
        window_end=None,
        triggered_by="manual",
    )


def stage_adc_access(db: SQLiteAdapter, run_id: int) -> None:
    StagingWriter(db).write_rows(
        "stg_orion_adc_access",
        run_id,
        "orion",
        "ORION ADC access tables",
        [
            {"customer_code": "C001", "account_code": "ACC001"},
            {"customer_code": "C001", "account_code": "ACC001"},
            {"customer_code": "C002", "account_number": "ACC002"},
            {"customer_code": None, "account_code": "ACC_SKIP"},
            {"customer_code": "C_SKIP", "account_code": None},
        ],
    )


def test_third_party_access_transform_loads_deduped_rows(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        stage_adc_access(db, run_id)

        result = ThirdPartyAccessTransformJob(db, StagingReader(db)).run(run_id, None, None)

        rows = db.query_all(
            """
            SELECT customer_code, account_code
            FROM third_party_access
            ORDER BY customer_code, account_code
            """
        )

        assert result.rows_read == 5
        assert result.rows_inserted == 2
        assert rows == [
            {"customer_code": "C001", "account_code": "ACC001"},
            {"customer_code": "C002", "account_code": "ACC002"},
        ]
    finally:
        db.close()


def test_third_party_access_transform_refreshes_on_rerun(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        first_run_id = create_test_run(db)
        stage_adc_access(db, first_run_id)
        job = ThirdPartyAccessTransformJob(db, StagingReader(db))
        job.run(first_run_id, None, None)

        second_run_id = create_test_run(db)
        StagingWriter(db).write_rows(
            "stg_orion_adc_access",
            second_run_id,
            "orion",
            "ORION ADC access tables",
            [{"customer_code": "C003", "account_code": "ACC003"}],
        )
        job.run(second_run_id, None, None)

        rows = db.query_all("SELECT customer_code, account_code FROM third_party_access")

        assert rows == [{"customer_code": "C003", "account_code": "ACC003"}]
    finally:
        db.close()


def test_third_party_access_transform_empty_staging_refreshes_to_empty(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        db.execute(
            "INSERT INTO third_party_access (customer_code, account_code) VALUES (?, ?)",
            ["OLD", "OLD_ACC"],
        )
        db.commit()
        run_id = create_test_run(db)

        result = ThirdPartyAccessTransformJob(db, StagingReader(db)).run(run_id, None, None)

        assert result.rows_read == 0
        assert result.rows_inserted == 0
        assert db.query_all("SELECT * FROM third_party_access") == []
    finally:
        db.close()

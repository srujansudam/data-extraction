from __future__ import annotations

from pathlib import Path

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.staging.writer import StagingWriter
from data_extraction.tracking.runs import ExtractionRunTracker
from data_extraction.transform.allowed_third_party import AllowedThirdPartyTransformJob


def create_test_run(db: SQLiteAdapter) -> int:
    return ExtractionRunTracker(db).start_run(
        run_type="daily",
        window_start=None,
        window_end=None,
        triggered_by="manual",
    )


def stage_allowed_inputs(db: SQLiteAdapter, run_id: int) -> None:
    writer = StagingWriter(db)
    writer.write_rows(
        "stg_orion_customer_links",
        run_id,
        "orion",
        "ORION.CUSTOMER_LINK",
        [
            {"customer_code": "C001", "linked_customer_code": "C010", "link_type_description": "Mandate"},
            {"customer_code": "C001", "linked_customer_code": "C011", "link_type_description": "Mandate"},
            {"customer_code": "C002", "linked_customer_code": "C020", "link_type_description": "POA"},
            {"customer_code": None, "linked_customer_code": "SKIP", "link_type_description": "Skip"},
        ],
    )
    writer.write_rows(
        "stg_orion_accounts",
        run_id,
        "orion",
        "ORION.ACCOUNT",
        [
            {"customer_code": "C001", "account_number": "ACC001"},
            {"customer_code": "C001", "account_number": "ACC002"},
        ],
    )


def test_allowed_third_party_transform_loads_account_and_customer_level_rows(
    tmp_path: Path,
) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        stage_allowed_inputs(db, run_id)

        result = AllowedThirdPartyTransformJob(db, StagingReader(db)).run(run_id, None, None)

        rows = db.query_all(
            """
            SELECT customer_code, account_code, reason
            FROM allowed_third_party
            ORDER BY customer_code, account_code
            """
        )

        assert result.rows_read == 4
        assert result.rows_inserted == 3
        assert rows == [
            {"customer_code": "C001", "account_code": "ACC001", "reason": "Mandate"},
            {"customer_code": "C001", "account_code": "ACC002", "reason": "Mandate"},
            {"customer_code": "C002", "account_code": None, "reason": "POA"},
        ]
    finally:
        db.close()


def test_allowed_third_party_transform_refreshes_on_rerun(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        first_run_id = create_test_run(db)
        stage_allowed_inputs(db, first_run_id)
        job = AllowedThirdPartyTransformJob(db, StagingReader(db))
        job.run(first_run_id, None, None)

        second_run_id = create_test_run(db)
        StagingWriter(db).write_rows(
            "stg_orion_customer_links",
            second_run_id,
            "orion",
            "ORION.CUSTOMER_LINK",
            [{"customer_code": "C003", "linked_customer_code": "C030", "link_type_description": "Other"}],
        )
        job.run(second_run_id, None, None)

        rows = db.query_all("SELECT customer_code, account_code, reason FROM allowed_third_party")

        assert rows == [{"customer_code": "C003", "account_code": None, "reason": "Other"}]
    finally:
        db.close()


def test_allowed_third_party_transform_empty_staging_refreshes_to_empty(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        db.execute(
            """
            INSERT INTO allowed_third_party (
                customer_code,
                account_code,
                reason
            )
            VALUES (?, ?, ?)
            """,
            ["OLD", "OLD_ACC", "OLD_REASON"],
        )
        db.commit()
        run_id = create_test_run(db)

        result = AllowedThirdPartyTransformJob(db, StagingReader(db)).run(run_id, None, None)

        assert result.rows_read == 0
        assert result.rows_inserted == 0
        assert db.query_all("SELECT * FROM allowed_third_party") == []
    finally:
        db.close()

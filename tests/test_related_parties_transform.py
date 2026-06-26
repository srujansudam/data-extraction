from __future__ import annotations

from pathlib import Path

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.staging.writer import StagingWriter
from data_extraction.tracking.runs import ExtractionRunTracker
from data_extraction.transform.related_parties import RelatedPartiesTransformJob


def create_test_run(db: SQLiteAdapter) -> int:
    return ExtractionRunTracker(db).start_run(
        run_type="daily",
        window_start=None,
        window_end=None,
        triggered_by="manual",
    )


def stage_related_party_inputs(db: SQLiteAdapter, run_id: int) -> None:
    writer = StagingWriter(db)
    writer.write_rows(
        "stg_hris_consolidated",
        run_id,
        "hris",
        "hris_consolidated",
        [
            {"worker_personnel_number": "P001", "identification_number": "STAFFID"},
        ],
    )
    writer.write_rows(
        "stg_orion_customer_links",
        run_id,
        "orion",
        "ORION.CUSTOMER_LINK",
        [
            {"customer_code": "CSTAFF", "linked_customer_code": "CLINKED"},
            {"customer_code": "CMISSING", "linked_customer_code": "CSKIP"},
        ],
    )
    writer.write_rows(
        "stg_flexcube_user_details",
        run_id,
        "flexcube",
        "FCBOV.SMTB_USER",
        [{"user_code": "U001", "id_card_number": "STAFFID"}],
    )
    writer.write_rows(
        "stg_orion_customer_identity_lookup",
        run_id,
        "orion",
        "ORION.EOM_CUSTOMER",
        [
            {"identification_number": "STAFFID", "customer_code": "CSTAFF"},
            {"identification_number": "RELID", "customer_code": "CREL"},
        ],
    )


def test_related_parties_transform_builds_hris_and_orion_rows(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        stage_related_party_inputs(db, run_id)

        result = RelatedPartiesTransformJob(db, StagingReader(db)).run(run_id, None, None)

        rows = db.query_all(
            """
            SELECT user_code, customer_code
            FROM related_parties
            ORDER BY customer_code
            """
        )

        assert result.rows_read == 3
        assert result.rows_inserted == 1
        assert rows == [
            {"user_code": "U001", "customer_code": "CLINKED"},
        ]
    finally:
        db.close()


def test_related_parties_transform_refreshes_final_table_on_rerun(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()

    try:
        create_all_tables(db)
        first_run_id = create_test_run(db)
        stage_related_party_inputs(db, first_run_id)
        job = RelatedPartiesTransformJob(db, StagingReader(db))
        job.run(first_run_id, None, None)

        second_run_id = create_test_run(db)
        writer = StagingWriter(db)
        writer.write_rows(
            "stg_flexcube_user_details",
            second_run_id,
            "flexcube",
            "FCBOV.SMTB_USER",
            [{"user_code": "U002", "id_card_number": "STAFF2"}],
        )
        writer.write_rows(
            "stg_orion_customer_identity_lookup",
            second_run_id,
            "orion",
            "ORION.EOM_CUSTOMER",
            [{"identification_number": "REL2", "customer_code": "CREL2"}],
        )
        writer.write_rows(
            "stg_hris_consolidated",
            second_run_id,
            "hris",
            "hris_consolidated",
            [{"worker_personnel_number": "P002", "identification_number": "STAFF2"}],
        )
        writer.write_rows(
            "stg_orion_customer_links",
            second_run_id,
            "orion",
            "ORION.CUSTOMER_LINK",
            [{"customer_code": "CREL2", "linked_customer_code": "CLINKED2"}],
        )

        job.run(second_run_id, None, None)

        rows = db.query_all("SELECT user_code, customer_code FROM related_parties")

        assert rows == []
    finally:
        db.close()

from __future__ import annotations

import json
from pathlib import Path

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.staging.lotus_corba_loader import LotusCorbaStagingLoader
from data_extraction.staging.writer import StagingWriter


def test_lotus_corba_ndjson_loads_existing_staging_tables(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()
    create_all_tables(db)
    output_path = tmp_path / "legal_rulings.ndjson"
    output_path.write_text(
        json.dumps(
            {
                "dataset": "legal_rulings",
                "database": "BOV\\LegalRulings.nsf",
                "view": "(EY - LR)",
                "replica_id": "C1256E4B:002152FC",
                "extracted_at": "2026-06-15T10:00:00Z",
                "row_number": 1,
                "note_id": "ABCD",
                "fields": {
                    "identity": "HEIR001",
                    "deceased_customer_code": "CUST2",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        loader = LotusCorbaStagingLoader(StagingWriter(db))
        inserted = loader.load_outputs(44, {"legal_rulings": output_path})

        assert inserted == 1
        staged = db.query_one(
            "SELECT source_payload FROM stg_lotus_legal_rulings WHERE run_id = ?",
            [44],
        )
        assert staged is not None
        payload = json.loads(staged["source_payload"])
        assert payload["deceased_customer_code"] == "CUST2"
        assert payload["id_card_no"] == "HEIR001"
        assert payload["source_mode"] == "corba"
        assert payload["source_file"] == "legal_rulings.ndjson"
        assert payload["source_path"] == str(output_path)
        assert payload["extracted_at"] == "2026-06-15T10:00:00Z"
    finally:
        db.close()


def test_lotus_corba_json_array_loads_bov_employee_aliases(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    db.connect()
    create_all_tables(db)
    output_path = tmp_path / "bov_employees.json"
    output_path.write_text(
        json.dumps(
            [
                {
                    "dataset": "bov_employees",
                    "extracted_at": "2026-06-15T10:00:00Z",
                    "fields": {"staff_no": "P001", "fcubs_no": "U001"},
                }
            ]
        ),
        encoding="utf-8",
    )

    try:
        loader = LotusCorbaStagingLoader(StagingWriter(db))
        loader.load_outputs(45, {"bov_employees": output_path})
        staged = db.query_one(
            "SELECT source_payload FROM stg_lotus_bov_employees WHERE run_id = ?",
            [45],
        )
        assert staged is not None
        payload = json.loads(staged["source_payload"])
        assert payload["staff_no"] == "P001"
        assert payload["flexcube_no"] == "U001"
    finally:
        db.close()

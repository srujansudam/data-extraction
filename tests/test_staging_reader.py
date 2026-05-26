from __future__ import annotations

from pathlib import Path

import pytest

from data_extraction.db.schema import create_staging_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.staging.writer import StagingWriter


def test_staging_reader_reads_payloads_for_run_id(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_staging_tables(db)
        writer = StagingWriter(db)
        writer.write_rows(
            staging_table="stg_orion_accounts",
            run_id=1,
            source_system="orion",
            source_object="ORION.ACCOUNT",
            rows=[{"account_number": "ACC001"}],
        )
        writer.write_rows(
            staging_table="stg_orion_accounts",
            run_id=2,
            source_system="orion",
            source_object="ORION.ACCOUNT",
            rows=[{"account_number": "ACC002"}],
        )

        reader = StagingReader(db)

        assert reader.read_payloads("stg_orion_accounts", run_id=1) == [
            {"account_number": "ACC001"}
        ]
    finally:
        db.close()


def test_staging_reader_returns_empty_list_for_no_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_staging_tables(db)
        reader = StagingReader(db)

        assert reader.read_payloads("stg_orion_accounts", run_id=999) == []
    finally:
        db.close()


@pytest.mark.parametrize(
    "staging_table",
    [
        "orion_accounts",
        "stg-orion-accounts",
        "stg_orion_accounts; DROP TABLE account_data",
    ],
)
def test_staging_reader_rejects_invalid_table_names(
    tmp_path: Path,
    staging_table: str,
) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    reader = StagingReader(db)

    with pytest.raises(ValueError, match="Invalid staging table name"):
        reader.read_payloads(staging_table, run_id=1)

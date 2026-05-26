from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from data_extraction.db.schema import create_all_tables
from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.staging.flexcube import (
    FLEXCUBE_DECEASED_CUSTOMERS_SQL,
    FLEXCUBE_USER_DETAILS_SQL,
    FlexcubeDeceasedCustomersStagingJob,
    FlexcubeUserDetailsStagingJob,
)
from data_extraction.jobs.staging.orion import (
    ORION_ACCOUNTS_SQL,
    ORION_ADC_ACCESS_SQL,
    ORION_CUSTOMERS_SQL,
    ORION_CUSTOMER_IDENTITY_LOOKUP_SQL,
    ORION_CUSTOMER_LINKS_SQL,
    ORION_TRANSACTIONS_SQL,
    OrionAccountsStagingJob,
    OrionAdcAccessStagingJob,
    OrionCustomerIdentityLookupStagingJob,
    OrionCustomerLinksStagingJob,
    OrionCustomersStagingJob,
    OrionTransactionsStagingJob,
)
from data_extraction.staging.writer import StagingWriter
from data_extraction.tracking.runs import ExtractionRunTracker


class FakeSourceClient:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.executed_sql: str | None = None
        self.executed_params: Iterable[Any] | None = None

    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.executed_sql = sql
        self.executed_params = params
        return self.rows


def create_test_run(db: SQLiteAdapter) -> int:
    run_tracker = ExtractionRunTracker(db)
    return run_tracker.start_run(
        run_type="daily",
        window_start="2026-05-25T00:00:00+02:00",
        window_end="2026-05-26T00:00:00+02:00",
        triggered_by="manual",
    )


@pytest.mark.parametrize(
    ("job_class", "expected_sql", "staging_table", "sample_row"),
    [
        (
            OrionAccountsStagingJob,
            ORION_ACCOUNTS_SQL,
            "stg_orion_accounts",
            {"account_number": "ACC001", "customer_code": "C001"},
        ),
        (
            OrionCustomersStagingJob,
            ORION_CUSTOMERS_SQL,
            "stg_orion_customers",
            {"customer_code": "C001", "customer_name": "Customer One"},
        ),
        (
            OrionCustomerLinksStagingJob,
            ORION_CUSTOMER_LINKS_SQL,
            "stg_orion_customer_links",
            {"customer_code": "C001", "linked_customer_code": "C002"},
        ),
        (
            OrionAdcAccessStagingJob,
            ORION_ADC_ACCESS_SQL,
            "stg_orion_adc_access",
            {"account_code": "ACC001", "adc_user_id": "U001"},
        ),
        (
            OrionCustomerIdentityLookupStagingJob,
            ORION_CUSTOMER_IDENTITY_LOOKUP_SQL,
            "stg_orion_customer_identity_lookup",
            {"identification_number": "ID001", "customer_code": "C001"},
        ),
        (
            FlexcubeDeceasedCustomersStagingJob,
            FLEXCUBE_DECEASED_CUSTOMERS_SQL,
            "stg_flexcube_deceased_customers",
            {"customer_code": "C001", "deceased_date": "2026-01-01"},
        ),
        (
            FlexcubeUserDetailsStagingJob,
            FLEXCUBE_USER_DETAILS_SQL,
            "stg_flexcube_user_details",
            {"user_code": "U001", "nt_username": "u001"},
        ),
    ],
)
def test_snapshot_staging_jobs_write_expected_table(
    tmp_path: Path,
    job_class: type[Any],
    expected_sql: str,
    staging_table: str,
    sample_row: dict[str, Any],
) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        source_client = FakeSourceClient(rows=[sample_row])
        job = job_class(
            db=db,
            source_client=source_client,
            staging_writer=StagingWriter(db),
        )

        result = job.run(run_id=run_id, window_start=None, window_end=None)
        rows = db.query_all(f"SELECT source_system, source_payload FROM {staging_table}")

        assert source_client.executed_sql == expected_sql
        assert source_client.executed_params is None
        assert result.rows_extracted == 1
        assert result.rows_inserted == 1
        assert rows[0]["source_system"] in {"orion", "flexcube"}
        assert json.loads(rows[0]["source_payload"]) == sample_row
    finally:
        db.close()


def test_orion_transactions_staging_job_uses_window_params_and_writes_payload(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test.db"
    db = SQLiteAdapter(str(db_path))
    db.connect()

    try:
        create_all_tables(db)
        run_id = create_test_run(db)
        sample_row = {
            "transaction_serial_number": "TX001",
            "transaction_reference": "REF001",
            "amount": -100.0,
        }
        source_client = FakeSourceClient(rows=[sample_row])
        job = OrionTransactionsStagingJob(
            db=db,
            source_client=source_client,
            staging_writer=StagingWriter(db),
        )

        result = job.run(
            run_id=run_id,
            window_start="2026-05-25T00:00:00+02:00",
            window_end="2026-05-26T00:00:00+02:00",
        )
        row = db.query_one("SELECT source_payload FROM stg_orion_transactions")

        assert source_client.executed_sql == ORION_TRANSACTIONS_SQL
        assert source_client.executed_params == ["2026-05-25", "2026-05-26"]
        assert result.rows_extracted == 1
        assert result.rows_inserted == 1
        assert row is not None
        assert json.loads(row["source_payload"]) == sample_row
    finally:
        db.close()

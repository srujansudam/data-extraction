from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.jobs.extract.credit_cards import CreditCardsExtractionJob
from data_extraction.jobs.extract.dormant_account import DormantAccountExtractionJob
from data_extraction.jobs.extract.eom_book_balance import EomBookBalanceExtractionJob
from data_extraction.jobs.extract.enquiry import EnquiryExtractionJob
from data_extraction.jobs.extract.exchange_rate import ExchangeRateExtractionJob
from data_extraction.jobs.extract.loans import LoansExtractionJob
from data_extraction.jobs.extract.office_accounts import OfficeAccountsExtractionJob
from data_extraction.jobs.factory import create_job


class FakeSourceClient:
    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        return []


def test_create_job_instantiates_office_accounts_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    source_client = FakeSourceClient()

    job = create_job(
        job_name="office_accounts",
        db=db,
        source_clients={"flexcube": source_client},
        timezone="UTC",
    )

    assert isinstance(job, OfficeAccountsExtractionJob)
    assert job.db is db
    assert job.source_client is source_client
    assert job.timezone == "UTC"


def test_create_job_instantiates_dormant_account_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    source_client = FakeSourceClient()

    job = create_job(
        job_name="dormant_account",
        db=db,
        source_clients={"flexcube": source_client},
        timezone="UTC",
    )

    assert isinstance(job, DormantAccountExtractionJob)
    assert job.db is db
    assert job.source_client is source_client
    assert job.timezone == "UTC"


def test_create_job_instantiates_exchange_rate_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    source_client = FakeSourceClient()

    job = create_job(
        job_name="exchange_rate",
        db=db,
        source_clients={"flexcube": source_client},
        timezone="UTC",
    )

    assert isinstance(job, ExchangeRateExtractionJob)
    assert job.db is db
    assert job.source_client is source_client
    assert job.timezone == "UTC"


def test_create_job_instantiates_loans_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    source_client = FakeSourceClient()

    job = create_job(
        job_name="loans",
        db=db,
        source_clients={"orion": source_client},
        timezone="UTC",
    )

    assert isinstance(job, LoansExtractionJob)
    assert job.db is db
    assert job.source_client is source_client
    assert job.timezone == "UTC"


def test_create_job_instantiates_eom_book_balance_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    source_client = FakeSourceClient()

    job = create_job(
        job_name="eom_book_balance",
        db=db,
        source_clients={"orion": source_client},
        timezone="UTC",
    )

    assert isinstance(job, EomBookBalanceExtractionJob)
    assert job.db is db
    assert job.source_client is source_client
    assert job.timezone == "UTC"


def test_create_job_instantiates_credit_cards_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    source_client = FakeSourceClient()

    job = create_job(
        job_name="credit_cards",
        db=db,
        source_clients={"flexcube": source_client},
        timezone="UTC",
    )

    assert isinstance(job, CreditCardsExtractionJob)
    assert job.db is db
    assert job.source_client is source_client
    assert job.timezone == "UTC"


def test_create_job_instantiates_enquiry_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))
    source_client = FakeSourceClient()

    job = create_job(
        job_name="enquiry",
        db=db,
        source_clients={"flexcube": source_client},
        timezone="UTC",
    )

    assert isinstance(job, EnquiryExtractionJob)
    assert job.db is db
    assert job.source_client is source_client
    assert job.timezone == "UTC"


def test_create_job_raises_clear_error_for_unknown_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))

    with pytest.raises(ValueError, match="Unknown job 'missing_job'"):
        create_job(
            job_name="missing_job",
            db=db,
            source_clients={"flexcube": FakeSourceClient()},
            timezone="UTC",
        )


def test_create_job_raises_clear_error_for_missing_source_client(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))

    with pytest.raises(ValueError, match="Missing source client for 'orion'"):
        create_job(
            job_name="loans",
            db=db,
            source_clients={},
            timezone="UTC",
        )

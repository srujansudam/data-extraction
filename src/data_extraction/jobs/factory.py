from __future__ import annotations

from collections.abc import Mapping

from data_extraction.connectors.base import SourceQueryClient
from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.jobs.base import BaseExtractionJob
from data_extraction.jobs.extract.dormant_account import DormantAccountExtractionJob
from data_extraction.jobs.extract.eom_book_balance import EomBookBalanceExtractionJob
from data_extraction.jobs.extract.exchange_rate import ExchangeRateExtractionJob
from data_extraction.jobs.extract.loans import LoansExtractionJob
from data_extraction.jobs.extract.office_accounts import OfficeAccountsExtractionJob


JOB_CLASSES: dict[str, type[BaseExtractionJob]] = {
    OfficeAccountsExtractionJob.job_name: OfficeAccountsExtractionJob,
    DormantAccountExtractionJob.job_name: DormantAccountExtractionJob,
    ExchangeRateExtractionJob.job_name: ExchangeRateExtractionJob,
    LoansExtractionJob.job_name: LoansExtractionJob,
    EomBookBalanceExtractionJob.job_name: EomBookBalanceExtractionJob,
}


def create_job(
    job_name: str,
    db: DatabaseAdapter,
    source_clients: Mapping[str, SourceQueryClient],
    timezone: str = "Europe/Malta",
) -> BaseExtractionJob:
    try:
        job_class = JOB_CLASSES[job_name]
    except KeyError as exc:
        available_jobs = ", ".join(sorted(JOB_CLASSES))
        raise ValueError(f"Unknown job '{job_name}'. Available jobs: {available_jobs}") from exc

    source_system = job_class.source_system
    try:
        source_client = source_clients[source_system]
    except KeyError as exc:
        available_clients = ", ".join(sorted(source_clients)) or "none"
        raise ValueError(
            f"Missing source client for '{source_system}' required by job '{job_name}'. "
            f"Available source clients: {available_clients}"
        ) from exc

    return job_class(db=db, source_client=source_client, timezone=timezone)

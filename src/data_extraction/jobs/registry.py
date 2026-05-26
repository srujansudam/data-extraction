from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobDefinition:
    job_name: str
    source_system: str
    target_table: str
    description: str


JOB_REGISTRY: dict[str, JobDefinition] = {
    "office_accounts": JobDefinition(
        job_name="office_accounts",
        source_system="flexcube",
        target_table="office_accounts",
        description="Extract office accounts from FCBOV.STTM_CUST_ACCOUNT.",
    ),
    "dormant_account": JobDefinition(
        job_name="dormant_account",
        source_system="flexcube",
        target_table="dormant_account",
        description="Extract dormant account snapshot from FCBOV.STTM_ACCOUNT_BALANCE.",
    ),
    "exchange_rate": JobDefinition(
        job_name="exchange_rate",
        source_system="flexcube",
        target_table="exchange_rate",
        description="Extract exchange rates from FCCREAD.BVTB_FXBV128_HIST.",
    ),
    "loans": JobDefinition(
        job_name="loans",
        source_system="orion",
        target_table="loans",
        description="Extract loan account details from ORION loan and product hierarchy tables.",
    ),
    "eom_book_balance": JobDefinition(
        job_name="eom_book_balance",
        source_system="orion",
        target_table="eom_book_balance",
        description="Extract EOM book balances from ORION EOM account tables.",
    ),
    "credit_cards": JobDefinition(
        job_name="credit_cards",
        source_system="flexcube",
        target_table="credit_cards",
        description="Extract credit card transactions from Flexcube teller tables.",
    ),
    "enquiry": JobDefinition(
        job_name="enquiry",
        source_system="flexcube",
        target_table="enquiry",
        description="Extract customer enquiry activity from Flexcube SMS logs.",
    ),
}


def list_jobs() -> list[JobDefinition]:
    return sorted(JOB_REGISTRY.values(), key=lambda job: job.job_name)


def get_job_definition(job_name: str) -> JobDefinition:
    try:
        return JOB_REGISTRY[job_name]
    except KeyError as exc:
        available_jobs = ", ".join(sorted(JOB_REGISTRY))
        raise ValueError(f"Unknown job '{job_name}'. Available jobs: {available_jobs}") from exc

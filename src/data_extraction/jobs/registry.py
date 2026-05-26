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
}


def list_jobs() -> list[JobDefinition]:
    return sorted(JOB_REGISTRY.values(), key=lambda job: job.job_name)


def get_job_definition(job_name: str) -> JobDefinition:
    try:
        return JOB_REGISTRY[job_name]
    except KeyError as exc:
        available_jobs = ", ".join(sorted(JOB_REGISTRY))
        raise ValueError(f"Unknown job '{job_name}'. Available jobs: {available_jobs}") from exc
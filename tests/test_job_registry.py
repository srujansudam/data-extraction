import pytest

from data_extraction.jobs.registry import get_job_definition, list_jobs


def test_list_jobs_returns_registered_jobs() -> None:
    jobs = list_jobs()
    job_names = {job.job_name for job in jobs}

    assert "office_accounts" in job_names
    assert "dormant_account" in job_names


def test_get_job_definition_returns_known_job() -> None:
    job = get_job_definition("office_accounts")

    assert job.job_name == "office_accounts"
    assert job.source_system == "flexcube"
    assert job.target_table == "office_accounts"


def test_get_job_definition_raises_for_unknown_job() -> None:
    with pytest.raises(ValueError, match="Unknown job"):
        get_job_definition("missing_job")
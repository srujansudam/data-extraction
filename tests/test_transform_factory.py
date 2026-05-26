from __future__ import annotations

from pathlib import Path

import pytest

from data_extraction.db.sqlite_adapter import SQLiteAdapter
from data_extraction.transform.account_data import AccountDataTransformJob
from data_extraction.transform.allowed_third_party import AllowedThirdPartyTransformJob
from data_extraction.transform.customer_data import CustomerDataTransformJob
from data_extraction.transform.factory import create_transform_job
from data_extraction.transform.legal_rulings import LegalRulingsTransformJob
from data_extraction.transform.related_parties import RelatedPartiesTransformJob
from data_extraction.transform.staff import StaffTransformJob
from data_extraction.transform.third_party_access import ThirdPartyAccessTransformJob
from data_extraction.transform.transaction_data import TransactionDataTransformJob
from data_extraction.transform.users import UsersTransformJob


@pytest.mark.parametrize(
    ("job_name", "expected_type"),
    [
        ("transform_account_data", AccountDataTransformJob),
        ("transform_customer_data", CustomerDataTransformJob),
        ("transform_transaction_data", TransactionDataTransformJob),
        ("transform_legal_rulings", LegalRulingsTransformJob),
        ("transform_staff", StaffTransformJob),
        ("transform_users", UsersTransformJob),
        ("transform_related_parties", RelatedPartiesTransformJob),
        ("transform_third_party_access", ThirdPartyAccessTransformJob),
        ("transform_allowed_third_party", AllowedThirdPartyTransformJob),
    ],
)
def test_create_transform_job_returns_supported_jobs(
    tmp_path: Path,
    job_name: str,
    expected_type: type,
) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))

    job = create_transform_job(job_name, db, timezone="Europe/Malta")

    assert isinstance(job, expected_type)
    assert job.job_name == job_name
    assert job.db is db


def test_create_transform_job_raises_for_unknown_job(tmp_path: Path) -> None:
    db = SQLiteAdapter(str(tmp_path / "test.db"))

    with pytest.raises(ValueError, match="Unknown transform job 'missing_transform'"):
        create_transform_job("missing_transform", db)

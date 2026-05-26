from __future__ import annotations

from collections.abc import Callable

from data_extraction.db.adapter import DatabaseAdapter
from data_extraction.staging.reader import StagingReader
from data_extraction.transform.account_data import AccountDataTransformJob
from data_extraction.transform.allowed_third_party import AllowedThirdPartyTransformJob
from data_extraction.transform.base import BaseTransformJob
from data_extraction.transform.customer_data import CustomerDataTransformJob
from data_extraction.transform.legal_rulings import LegalRulingsTransformJob
from data_extraction.transform.related_parties import RelatedPartiesTransformJob
from data_extraction.transform.staff import StaffTransformJob
from data_extraction.transform.third_party_access import ThirdPartyAccessTransformJob
from data_extraction.transform.transaction_data import TransactionDataTransformJob
from data_extraction.transform.users import UsersTransformJob


def create_transform_job(
    job_name: str,
    db: DatabaseAdapter,
    timezone: str = "Europe/Malta",
) -> BaseTransformJob:
    staging_reader = StagingReader(db)
    factories: dict[str, Callable[[], BaseTransformJob]] = {
        "transform_account_data": lambda: AccountDataTransformJob(
            db=db,
            staging_reader=staging_reader,
            timezone=timezone,
        ),
        "transform_customer_data": lambda: CustomerDataTransformJob(
            db=db,
            staging_reader=staging_reader,
            timezone=timezone,
        ),
        "transform_transaction_data": lambda: TransactionDataTransformJob(
            db=db,
            staging_reader=staging_reader,
            timezone=timezone,
        ),
        "transform_legal_rulings": lambda: LegalRulingsTransformJob(
            db=db,
            staging_reader=staging_reader,
            timezone=timezone,
        ),
        "transform_staff": lambda: StaffTransformJob(
            db=db,
            staging_reader=staging_reader,
            timezone=timezone,
        ),
        "transform_users": lambda: UsersTransformJob(db=db, timezone=timezone),
        "transform_related_parties": lambda: RelatedPartiesTransformJob(
            db=db,
            staging_reader=staging_reader,
            timezone=timezone,
        ),
        "transform_third_party_access": lambda: ThirdPartyAccessTransformJob(
            db=db,
            staging_reader=staging_reader,
            timezone=timezone,
        ),
        "transform_allowed_third_party": lambda: AllowedThirdPartyTransformJob(
            db=db,
            staging_reader=staging_reader,
            timezone=timezone,
        ),
    }

    try:
        return factories[job_name]()
    except KeyError as exc:
        supported_jobs = ", ".join(sorted(factories))
        raise ValueError(
            f"Unknown transform job '{job_name}'. Supported jobs: {supported_jobs}"
        ) from exc

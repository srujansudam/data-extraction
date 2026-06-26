from __future__ import annotations

from data_extraction.pipeline.definitions import (
    DIRECT_JOB_ORDER,
    STAGING_JOB_ORDER,
    TRANSFORM_JOB_ORDER,
    get_full_pipeline_order,
)


def test_pipeline_definitions_include_expected_direct_jobs_only() -> None:
    assert DIRECT_JOB_ORDER == [
        "office_accounts",
        "dormant_account",
        "exchange_rate",
        "loans",
        "eom_book_balance",
        "credit_cards",
        "enquiry",
    ]


def test_pipeline_definitions_include_expected_staging_jobs_only() -> None:
    assert STAGING_JOB_ORDER == [
        "orion_accounts",
        "orion_customers",
        "flexcube_deceased_customers",
        "orion_transactions",
        "orion_customer_links",
        "orion_adc_access",
        "flexcube_user_details",
        "orion_customer_identity_lookup",
        "hris_consolidated",
        "lotus_bov_employees",
        "lotus_legal_rulings",
        "lotus_garnishee_orders",
        "lotus_poa_revocation",
        "lotus_discrepancies_management",
    ]


def test_pipeline_definitions_include_expected_transform_jobs_only() -> None:
    assert TRANSFORM_JOB_ORDER == [
        "transform_account_data",
        "transform_customer_data",
        "transform_transaction_data",
        "transform_legal_rulings",
        "transform_staff",
        "transform_users",
        "transform_related_parties",
        "transform_third_party_access",
        "transform_allowed_third_party",
    ]


def test_get_full_pipeline_order_groups_all_pipeline_phases() -> None:
    assert get_full_pipeline_order() == {
        "direct": DIRECT_JOB_ORDER,
        "staging": STAGING_JOB_ORDER,
        "transform": TRANSFORM_JOB_ORDER,
    }

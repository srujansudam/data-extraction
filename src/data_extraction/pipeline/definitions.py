from __future__ import annotations

DIRECT_JOB_ORDER = [
    "office_accounts",
    "dormant_account",
    "exchange_rate",
    "loans",
    "eom_book_balance",
    "credit_cards",
    "enquiry",
]

SOURCE_DISPLAY_NAMES = {
    "orion": "ORION",
    "flexcube": "Flexcube",
    "hris": "HRIS",
    "lotus_notes": "Lotus Notes",
}

STAGING_JOB_ORDER = [
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

STAGING_JOB_SOURCES = {
    "orion_accounts": "orion",
    "orion_customers": "orion",
    "orion_transactions": "orion",
    "orion_customer_links": "orion",
    "orion_adc_access": "orion",
    "orion_customer_identity_lookup": "orion",
    "flexcube_deceased_customers": "flexcube",
    "flexcube_user_details": "flexcube",
    "hris_consolidated": "hris",
    "lotus_bov_employees": "lotus_notes",
    "lotus_legal_rulings": "lotus_notes",
    "lotus_garnishee_orders": "lotus_notes",
    "lotus_poa_revocation": "lotus_notes",
    "lotus_discrepancies_management": "lotus_notes",
}

TRANSFORM_JOB_ORDER = [
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


def get_full_pipeline_order() -> dict[str, list[str]]:
    return {
        "direct": DIRECT_JOB_ORDER,
        "staging": STAGING_JOB_ORDER,
        "transform": TRANSFORM_JOB_ORDER,
    }

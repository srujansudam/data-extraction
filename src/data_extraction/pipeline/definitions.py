from __future__ import annotations

STAGING_JOB_ORDER = [
    "orion_accounts",
    "orion_customers",
    "flexcube_deceased_customers",
    "orion_transactions",
    "orion_customer_links",
    "orion_adc_access",
    "flexcube_user_details",
    "orion_customer_identity_lookup",
    "hris_staff_identification",
    "hris_personnel_contact_detail",
    "hris_appendix_3_crm",
    "lotus_bov_employees",
    "lotus_legal_rulings",
]

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

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class FakeSourceClient:
    def __init__(self) -> None:
        self.executed_queries: list[tuple[str, list[Any] | None]] = []

    def query_all(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        params_list = list(params) if params is not None else None
        self.executed_queries.append((sql, params_list))

        normalized_sql = " ".join(sql.upper().split())

        if "FCBOV.STTM_CUST_ACCOUNT" in normalized_sql:
            return [
                {
                    "office_account_number": "OFF001",
                    "customer_code": "CUST1",
                    "office_account_name": "Office Operations",
                }
            ]

        if "FCBOV.STTM_ACCOUNT_BALANCE" in normalized_sql:
            return [{"account_number": "ACC_DORMANT", "date": None, "dormant": "Y"}]

        if "FCCREAD.BVTB_FXBV128_HIST" in normalized_sql:
            return [
                {
                    "transaction_id": "FX001",
                    "customer_code": "CUST1",
                    "base_currency": "EUR",
                    "transaction_type": "FXSA",
                    "branch": "301",
                    "amount": 100.0,
                    "transaction_currency": "USD",
                    "exchange_rate": 1.08,
                    "middle_rate": 1.07,
                    "transaction_date": "2026-05-25",
                }
            ]

        if "FROM ORION.LOAN LOAN" in normalized_sql:
            return [
                {
                    "account_number": "ACC_LOAN",
                    "customer_code": "CUST1",
                    "product_lvl_6": "Loans",
                    "product_lvl_7": "Personal Loans",
                    "drawdown_expiry_date": "2027-01-31",
                }
            ]

        if "FROM ORION.EOM_ACCOUNT EOM_ACCOUNT" in normalized_sql:
            return [
                {
                    "eom_date": "2026-04-30",
                    "customer_code": "CUST1",
                    "account_number": "ACC1",
                    "product_lvl_7": "Current Account",
                    "book_balance": 1500.25,
                }
            ]

        if "FCBOV.DETB_RTL_TELLER_EE_CU" in normalized_sql:
            return [
                {
                    "transaction_reference": "301CARD001",
                    "user_code": "U001",
                    "date": "2026-05-25",
                    "customer_code": "CUST1",
                    "branch_code": "301",
                    "amount": None,
                    "credit_card_number": "411111******1111",
                }
            ]

        if "SMTB_SMS_ACTION_LOG" in normalized_sql:
            return [
                {
                    "user_code": "U001",
                    "function_id": "STDCIF",
                    "start_time": "2026-05-25 09:00:00",
                    "action_time": "2026-05-25 09:01:00",
                    "terminal_id": "TERM001",
                    "branch_code": "301",
                    "description": "Customer Information",
                    "action": "EXECUTEQUERY",
                    "pkvals": "CUST1M",
                    "breadcrumbs": "Customer -> Enquiry -> Details",
                    "error_msg": None,
                }
            ]

        if "FROM ORION.ACCOUNT ACCOUNT" in normalized_sql:
            return [
                {
                    "account_number": "ACC1",
                    "acc_designation": "Current",
                    "customer_code": "CUST1",
                    "account_currency": "Euro",
                    "account_opening_date": "2020-01-15",
                },
                {
                    "account_number": "ACC2",
                    "acc_designation": "Savings",
                    "customer_code": "CUST2",
                    "account_currency": "Euro",
                    "account_opening_date": "2019-06-10",
                },
            ]

        if "ORION ADC ACCESS TABLES" in normalized_sql or "ORION.ADC_CONTRACT" in normalized_sql:
            return [
                {
                    "account_code": "ACC1",
                    "adc_user_id": "ADC001",
                    "login_id": "adc.user",
                    "user_status_description": "Active",
                    "third_party_access_description": "Allowed",
                    "customer_code": "CUST1",
                    "customer_name": "Test Customer One",
                }
            ]

        if "FROM ORION.CUSTOMER CUSTOMER" in normalized_sql and "CUSTOMER_LINK" not in normalized_sql:
            return [
                {
                    "customer_code": "CUST1",
                    "phone_number": "99000001",
                    "identification_number": "ID001",
                    "customer_name": "Test Customer One",
                    "date_of_birth": "1990-05-10",
                    "address_1": "1 Main Street",
                    "address_2": "",
                    "city": "Valletta",
                    "country": "MT",
                    "zip_code": "VLT001",
                },
                {
                    "customer_code": "CUST2",
                    "phone_number": "99000002",
                    "identification_number": "ID002",
                    "customer_name": "Test Customer Two",
                    "date_of_birth": "1980-01-20",
                    "address_1": "2 Side Street",
                    "address_2": "",
                    "city": "Sliema",
                    "country": "MT",
                    "zip_code": "SLM002",
                },
            ]

        if "ORION.V_ACC_FINANCIAL_TRANSACTIONS" in normalized_sql:
            return [
                {
                    "transaction_serial_number": "TX001",
                    "first_loan_drawdown_date": "2022-03-01",
                    "transaction_reference": "REF001",
                    "channel_lvl_4": "Branch",
                    "transaction_date": "2026-05-25",
                    "transaction_time": "10:15",
                    "cheque_number": None,
                    "detailed_statement_description": "Cash withdrawal",
                    "user_code": "U001",
                    "amount": -50.0,
                    "transaction_code_description": "Withdrawal",
                    "transaction_product_description": "Current Account",
                    "account_number": "ACC1",
                }
            ]

        if "ORION.CUSTOMER_LINK" in normalized_sql:
            return [
                {
                    "customer_code": "CUST1",
                    "linked_customer_code": "CUST_LINKED",
                    "link_type_description": "Mandate",
                }
            ]

        if "FCBOV.STTMS_CUST_PERSONAL_EE_CU" in normalized_sql:
            return [{"customer_code": "CUST2", "deceased_date": "2024-12-31"}]

        if "FCBOV.CSTM_FUNCTION_USERDEF_FIELDS" in normalized_sql:
            return [
                {
                    "user_code": "U001",
                    "user_name": "Dry Run User",
                    "nt_username": "dry.user",
                    "id_card_number": "ID001",
                }
            ]

        if "ORION.F_CUSTOMER_IDENTITY" in normalized_sql:
            return [
                {"identification_number": "ID001", "customer_code": "CUST1"},
                {"identification_number": "ID002", "customer_code": "CUST2"},
                {"identification_number": "RELID001", "customer_code": "CUST_REL"},
            ]

        if 'FROM "STAFF IDENTIFICATION"' in normalized_sql:
            return [
                {
                    "personnel_number": "P001",
                    "name": "Dry Run Staff",
                    "identification_number": "ID001",
                    "department": "Audit",
                    "primary_position_description": "Auditor",
                    "primary_position_category": "Professional",
                }
            ]

        if 'FROM "PERSONNEL CONTACT DETAIL"' in normalized_sql:
            return [
                {
                    "personnel_number": "P001",
                    "national_id": "ID001",
                    "first_name": "Dry",
                    "last_name": "Staff",
                    "department_name": "Audit",
                    "relationship_type": "Relative",
                    "rel_first_name": "Related",
                    "rel_last_name": "Person",
                    "rel_national_id": "RELID001",
                    "rel_gender": "F",
                }
            ]

        if 'FROM "APPENDIX 3 (CRM)"' in normalized_sql:
            return [
                {
                    "personnel_number": "P001",
                    "bovnt_custom": "dry.user",
                    "identity_email": "dry.user@example.test",
                    "id_number": "ID001",
                    "full_name": "Dry Run Staff",
                    "exco_member": "N",
                    "department_name": "Audit",
                    "section_name": "Internal Audit",
                    "sub_section": "Data",
                    "branch_posted": "Head Office",
                    "main_department": "Audit",
                    "main_section": "Internal Audit",
                    "main_sub_section": "Data",
                    "primary_position": "Auditor",
                    "primary_position_description": "Auditor",
                    "primary_position_category": "Professional",
                    "manager_name": "Audit Manager",
                    "manager_position": "Manager",
                    "manager_email": "manager@example.test",
                    "last_name": "Staff",
                    "first_name": "Dry",
                }
            ]

        return []

    def fetch_endpoint(self, endpoint_name: str) -> list[dict[str, Any]]:
        if endpoint_name != "hris_consolidated":
            return []
        return [
            {
                "hris_employee_id": "HRIS001",
                "worker_personnel_number": "P001",
                "manager_personnel_number": "M001",
                "first_name": "Dry",
                "last_name": "Staff",
                "full_name": "Dry Run Staff",
                "email": "dry.user@example.test",
                "identification_number": "ID001",
                "worker_status": "Active",
                "employment_start_date": "2020-01-01",
                "employment_end_date": None,
                "is_primary_position": True,
                "department": "Audit",
                "department_number": "D001",
                "section": "Internal Audit",
                "subsection": "Data",
                "chief_officer": "Chief Audit",
                "position_id": "AUD",
                "position_type": "Professional",
                "position_description": "Auditor",
                "parent_position_id": "MGR",
                "parent_position_description": "Manager",
                "manager_name": "Audit Manager",
                "manager_email": "manager@example.test",
                "manager_bovnt": "manager.user",
                "nt_username": "dry.user",
                "created_on": "2026-01-01T00:00:00Z",
                "modified_on": "2026-05-25T00:00:00Z",
                "state_code": 0,
                "status_code": 1,
                "_raw_record": {"crfe9_hrisemployeeid": "HRIS001"},
            }
        ]

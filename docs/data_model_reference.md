# Data Model Reference

## Final model tables

The final SQLite model includes:

- account_data
- dormant_account
- customer_data
- third_party_access
- allowed_third_party
- related_parties
- transaction_data
- users
- staff
- credit_cards
- exchange_rate
- enquiry
- eom_book_balance
- office_accounts
- legal_rulings
- loans

## Model updates agreed

The proposed data model has been updated with:

- New table: staff
- New field: office_accounts.office_account_name

## Fields intentionally not populated

Do not populate these fields for now:

- transaction_data.initiator_id
- transaction_data.statement_description
- credit_cards.amount

These fields should remain nullable in the SQLite schema.

## Direct extraction tables

These tables can be loaded directly from one source query:

### office_accounts

Source: Flexcube

Table: FCBOV.STTM_CUST_ACCOUNT

Logic:

```sql
SELECT
    CUST_AC_NO AS office_account_number,
    CUST_NO AS customer_code,
    AC_DESC AS office_account_name
FROM FCBOV.STTM_CUST_ACCOUNT
WHERE ACCOUNT_CLASS LIKE '%OFF%'

Load strategy:

Current snapshot refresh
Delete existing rows before insert
dormant_account

Source: Flexcube

Table: fcbov.sttm_account_balance

Logic:

SELECT
    cust_ac_no AS account_number,
    NULL AS date,
    ac_stat_dormant AS dormant
FROM fcbov.sttm_account_balance
WHERE ac_stat_dormant = 'Y'

Load strategy:

Full daily snapshot
Duplicates allowed
date is not populated by extraction
Multi-source final tables

These should use staging plus transformation. Do not force into one large source query.

customer_data

Sources:

ORION.CUSTOMER
ORION.PERSONAL_CUSTOMER
FCUB.CUSTOMER_ADDRESS
FCBOV.sttms_cust_personal_ee_cu

Notes:

creation_date means account opening date
age is calculated at extraction date
phone_number is mobile number
deceased_date comes from Flexcube field
transaction_data

Source:

ORION.V_ACC_FINANCIAL_TRANSACTIONS
ORION.LOAN for first_loan_drawdown_date where needed

Notes:

amount is signed
debit is negative
credit is positive
transaction_serial_number is unique
extract all transactions with no user-code filter
staff

Sources:

HRIS Staff Identification
HRIS Personnel Contact Detail
HRIS Appendix 3 CRM
Lotus Notes BOV Employees
Flexcube user reference query
ORION customer/account lookup

Notes:

staff and users are different concepts
one staff/user can have multiple account rows
legal_rulings

Sources:

Lotus Notes Succession & Legal rulings
ORION account lookup from deceased customer code

Notes:

ID Card No is heir/ruling holder ID
deceased_account_number is derived by joining deceased customer code to account number
multiple rows per deceased customer are allowed if multiple accounts exist
related_parties

Sources:

HRIS Personnel Contact Detail
ORION.CUSTOMER_LINK

Notes:

Include all HRIS relationship types
Do not store relationship_type in final table for now
third_party_access and allowed_third_party

Source:

ADC scenario logic from Accounts assigned under customers on ADC that differ from mandate instructions

Notes:

third_party_access.account_code is same as account number
only keep customer_code and account_code for third_party_access
allowed_third_party can be customer-level and account-level
no need to validate reason
enquiry

Sources:

SMTB_SMS_LOG
SMTB_SMS_LOG_HIST
SMTB_SMS_ACTION_LOG
SMTB_SMS_ACTION_LOG_HIST
SMTB_FUNCTION_DESCRIPTION

Notes:

Only EXECUTEQUERY actions
Union current and history
Use breadcrumb logic from data mapping
error_msg is action log description
do not extract resp_xml
unique key is user_id + function_id + start_time
pkvals stored as-is
exchange_rate

Source:

FCCREAD.BVTB_FXBV128_HIST

Notes:

customer_code comes from EOM_CUSTOMER
CONTRACT_REF_NO is unique
extract all FX, scenario filters happen in tool logic
eom_book_balance

Sources:

ORION.EOM_ACCOUNT
ORION.EOM_ACCOUNT_HOLDER
ORION.EOM_CUSTOMER
ORION.EOM_V_PRODUCT_LEVEL_7

Notes:

daily extraction with deduplication
2-year backfill equals 24 months
extract all product/account types
loans

Sources:

ORION.LOAN
ORION.ADVANCE
ORION.AGREEMENT
ORION.ACCOUNT
product hierarchy tables

Notes:

drawdown_expiry_date comes from daily source, not monthly
only extract fields present in final model
loan change log is derived, not extracted
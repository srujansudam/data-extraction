# Data Extraction Build Context

## Project

Project name: data-extraction

Purpose: Build an internal audit data extraction service that runs daily on a client VM, connects to ORION, Flexcube, HRIS and Lotus Notes, and loads data into an encrypted SQLite-based Internal Audit database.

The service will eventually be fully packaged as an executable. The client VM should not need Python libraries installed separately.

## Architecture

Source systems:
- ORION: Oracle DB
- Flexcube: Oracle DB
- HRIS: Oracle views, accessed using API/DB credentials
- Lotus Notes: Excel extracts by default; Java 8 CORBA is a supported optional Phase 2 mode

Secrets:
- Production credentials will come from a local KeePass/KeePassXC `.kdbx` database read with PyKeePass
- Local development uses .env through EnvironmentSecretProvider
- Do not hardcode credentials

Database:
- SQLite through SQLiteAdapter
- SQLite SEE is the selected production encryption approach
- DB implementation must remain behind DatabaseAdapter
- Do not make business jobs depend directly on sqlite3

Extraction pattern:
- Daily extraction uses previous calendar day
- Initial backfill is 2 years
- Some final data model tables are direct source loads
- Some final data model tables require multiple sources and should use staging + transform pattern

Important:
- Scenario SQL document is the source of truth for extraction logic
- Existing data mapping sheet is only a reference
- Proposed data model is fixed except:
  - Add staff table
  - Add office_accounts.office_account_name
- These fields are intentionally not populated:
  - transaction_data.initiator_id
  - transaction_data.statement_description
  - credit_cards.amount

## Final data model tables

Final model tables:
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

Tracking tables:
- extraction_run
- extraction_job_run
- extraction_job_watermark
- extraction_error_log
- source_file_ingestion
- data_quality_check

## Existing implemented foundation

Already implemented:
- Config loader
- Logging
- Date window utilities
- SQLiteAdapter
- Schema creation
- Tracking helpers
- BaseExtractionJob
- OracleConnector skeleton
- SourceQueryClient protocol
- OfficeAccountsExtractionJob
- DormantAccountExtractionJob
- Job registry

All changes must keep pytest and ruff passing.

## Existing direct jobs

### office_accounts

Source: Flexcube

SQL:
```sql
SELECT
    CUST_AC_NO AS office_account_number,
    CUST_NO AS customer_code,
    AC_DESC AS office_account_name
FROM FCBOV.STTM_CUST_ACCOUNT
WHERE ACCOUNT_CLASS LIKE '%OFF%'

Load strategy:

Snapshot refresh
Delete existing office_accounts rows before insert
dormant_account

Source: Flexcube

SQL:

SELECT
    cust_ac_no AS account_number,
    NULL AS date,
    ac_stat_dormant AS dormant
FROM fcbov.sttm_account_balance
WHERE ac_stat_dormant = 'Y'

Load strategy:

Full daily snapshot
Duplicates allowed
Do not fill date as part of extraction
Multi-source logic

Do not force every final table into one source query.

Use staging + transform for multi-source final tables.

Examples:

staff = HRIS + Lotus Notes BOV Employees + Flexcube user details + customer/account lookup
legal_rulings = Lotus Notes legal rulings + account lookup by deceased customer code
customer_data = ORION customer + personal customer + FCUB address + Flexcube deceased date
related_parties = HRIS relationship data + ORION customer links
transaction_data = ORION transaction data + loan first drawdown date where required

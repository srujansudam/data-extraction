# Solution Finalisation

## Current Production Architecture

The production data extraction service is a packaged Windows executable that:

- reads Oracle source credentials from a local KeePass/KeePassXC vault using PyKeePass
- connects to ORION, Flexcube, and HRIS
- ingests Lotus Notes data from configured Excel extracts by default
- optionally extracts dedicated Lotus views through the Java 8 CORBA reader
- loads direct and staged/transform data into a local SQLite database
- encrypts the production SQLite database with SQLite SEE
- records pipeline runs, job runs, watermarks, and errors

The client VM does not need a separate Python installation.

## Unified Application Schema

The data extraction tool owns one unified local SQLite application schema. Running
`init-db` creates the complete schema idempotently:

- extraction control and tracking tables
- all ORION, Flexcube, HRIS, and Lotus staging tables
- all final GIA data model tables
- the active auditor workflow/review schema, including scenario, trigger,
  result-association, change-log, and review log tables
- required indexes and uniqueness constraints

No manual SQLite table creation is required on the client VM. Daily and backfill
runs expect this schema to have been initialized; they are not a substitute for
the explicit first-run `init-db` step.

### Canonical Entities And Relationships

`account_data` and `users` are canonical entity tables retained for the auditor
workflow/review application and other consumers that require one row per entity:

- `account_data` contains one row per `account_number`
- `users` contains one row per `user_code`

The transforms merge populated source values deterministically when creating
those canonical rows. Their compatibility `customer_code` and `account_number`
columns represent one deterministic observed relationship; they are not the
complete relationship set.

Full source relationship coverage is preserved in:

- `account_customer_association` for every distinct account/customer link
- `user_customer_account_association` for every distinct
  user/customer/account link

Scenario and review logic must use these association tables whenever all joint
accounts, customer relationships, or user account assignments are required.

## Source Systems

- ORION: Oracle
- Flexcube: Oracle
- HRIS: Oracle views
- Lotus Notes: Excel ingestion by default, optional Java 8 CORBA Phase 2

## Credentials

The selected production credential store is a local KeePass/KeePassXC `.kdbx` database.

Recommended files:

```text
secrets\
  internal_audit_secrets.kdbx
  internal_audit_secrets.keyx
```

The direct `keepass` provider is the production path. The `keepass_cli` provider is retained only as a fallback.

## Database Encryption

Production uses SQLite SEE with:

```yaml
database:
  encryption: see
  secret_ref: INTERNAL_AUDIT_DB_KEY
```

The packaged application must use the client-licensed SEE-enabled `sqlite3.dll`. SEE source, binaries, activation keys, and database keys are not included in the repository or release bundle.

## Lotus Notes

The current production-supported Lotus Notes mode is Excel:

```yaml
sources:
  lotus_notes:
    mode: excel
```

Java CORBA is a supported optional Phase 2 mode. Keep Excel as the default fallback and enable CORBA only after VM validation.

CORBA requires:

- a client-approved Java 8 runtime, preferably IBM Semeru/OpenJ9 8
- BOV/client-supplied `notes.jar` and `ncso.jar`
- client-supplied `diiop_ior.txt`
- network access to `10.64.100.15:63148`
- KeePass entry `LOTUS_NOTES_PROD`
- read access to the five configured NSF databases and dedicated EY views

## Config Changes On The VM

Create `config\config.yaml` from `config\config.production.template.yaml`.

Update only deployment-specific settings:

- database and logging paths, if different
- KeePass database/key-file paths
- ORION, Flexcube, and HRIS secret references
- Lotus Excel file paths
- optional Lotus CORBA paths and mappings
- SEE activation key only if required by the licensed SEE build

Do not store real credentials or the SQLite database key in `config.yaml`.

## KeePass Entries

Create:

- `ORION_DB_PROD`
- `FLEXCUBE_DB_PROD`
- `HRIS_DB_PROD`
- `INTERNAL_AUDIT_DB_KEY`
- `LOTUS_NOTES_PROD` when CORBA is enabled

Oracle entries:

- UserName: database username
- Password: database password
- Custom fields: `host`, `port`, `service_name`

SQLite SEE key entry:

- Password: generated long random key
- Optional custom field: `key`

Lotus CORBA entry:

- UserName: Lotus Notes username
- Password: Lotus Notes password

## Lotus Incoming Folder

Place the configured files under `lotus_notes\incoming\`:

- BOV employees
- legal rulings
- garnishee orders
- POA revocation
- discrepancies management

The exact filenames are controlled by `sources.lotus_notes.files` in `config.yaml`.

## SEE Runtime Setup

Client IT must:

1. Obtain the licensed SEE source/build.
2. Compile the selected SEE-enabled `sqlite3.dll`.
3. Copy the DLL beside `data-extraction.exe`, and replace any bundled internal SQLite DLL if applicable.
4. Create the `INTERNAL_AUDIT_DB_KEY` KeePass entry.
5. Run preflight to confirm `PRAGMA textkey` is accepted.

See `docs\sqlite_see_setup.md`.

## Operational Command Sequence

```powershell
.\data-extraction.exe --config .\config\config.yaml preflight
.\data-extraction.exe --config .\config\config.yaml test-secret ORION_DB_PROD
.\data-extraction.exe --config .\config\config.yaml test-source all
.\data-extraction.exe --config .\config\config.yaml init-db
.\data-extraction.exe --config .\config\config.yaml run-dry-pipeline --reset-db
.\data-extraction.exe --config .\config\config.yaml run-backfill
.\data-extraction.exe --config .\config\config.yaml run-daily
```

Run `preflight`, `test-secret`, and `test-source all` before the first extraction.

For Phase 2 CORBA validation:

```powershell
.\data-extraction.exe --config .\config\config.yaml test-secret LOTUS_NOTES_PROD
.\data-extraction.exe --config .\config\config.yaml test-lotus-corba
.\data-extraction.exe --config .\config\config.yaml extract-lotus-corba
```

# Client VM Setup Checklist

## 1. Objective

Deploy the Internal Audit Data Extraction application on the client-provided Windows VM.

The application extracts data from ORION, Flexcube, HRIS, and Lotus Notes Excel extracts, loads the local SQLite SEE database, and tracks extraction runs, job status, errors, and data quality checks.

## 2. Target Folder Structure

Recommended base folder:

```text
C:\InternalAuditDataExtraction\
  data-extraction.exe
  config\
    config.yaml
  data\
  logs\
  lotus_notes\
    incoming\
  secrets\
    internal_audit_secrets.kdbx
    internal_audit_secrets.keyx
  scripts\
    get_keepass_secret.ps1
  tools\
    sqlite-see\
  java\
    lotus-corba-reader\
```

Create the folder structure using:

```powershell
.\scripts\setup_client_vm_folders.ps1 -BasePath "C:\InternalAuditDataExtraction"
```

## 3. Files To Copy

Copy:

- `data-extraction.exe`
- `config\config.production.template.yaml`, then copy it to `config\config.yaml`
- `scripts\get_keepass_secret.ps1` only if using fallback `keepass_cli`
- `scripts\README_keepass_setup.md` only if using fallback `keepass_cli`
- `docs\`
- `data\`
- `logs\`
- SEE-enabled `sqlite3.dll` beside `data-extraction.exe`

Do not copy `.env`, local development databases, local logs, test files, SEE source, SEE activation keys, or real credentials into the release bundle. The client-created `.kdbx` and `.keyx` files should be created or placed on the VM under the approved `secrets\` folder, not committed to the repository.

## 4. Config Setup

The production config should contain:

- database path
- logging folder
- source enablement flags
- `secrets.provider: keepass`
- KeePass secret references
- Lotus Notes mode and file paths

Production database encryption should be:

```yaml
database:
  encryption: see
  secret_ref: INTERNAL_AUDIT_DB_KEY
  see_activation_key: ""
```

Follow `docs\sqlite_see_setup.md`. Copy the SEE-enabled `sqlite3.dll` beside `data-extraction.exe` before running an encrypted DB.

## 5. KeePass Setup

Production should use the direct KeePass provider:

```yaml
secrets:
  provider: keepass
  keepass:
    database_path: secrets/internal_audit_secrets.kdbx
    key_file_path: secrets/internal_audit_secrets.keyx
    password_env_var: ""
```

Create KeePass entries with titles matching the configured secret refs:

- `ORION_DB_PROD`
- `FLEXCUBE_DB_PROD`
- `HRIS_DB_PROD`
- `INTERNAL_AUDIT_DB_KEY`

For Oracle source entries:

- UserName: DB username
- Password: DB password
- Custom fields:
  - `host`
  - `port`
  - `service_name`

The direct provider returns this shape for Oracle source secrets:

```json
{
  "username": "...",
  "password": "...",
  "host": "...",
  "port": "1521",
  "service_name": "..."
}
```

The SQLite SEE database key secret `INTERNAL_AUDIT_DB_KEY` should be stored as the entry Password or custom field `key`, returning:

```json
{
  "key": "long-random-passphrase"
}
```

The application logs only returned secret keys, never secret values.

Test each secret reference:

```powershell
.\data-extraction.exe --config .\config\config.yaml test-secret ORION_DB_PROD
.\data-extraction.exe --config .\config\config.yaml test-secret FLEXCUBE_DB_PROD
.\data-extraction.exe --config .\config\config.yaml test-secret HRIS_DB_PROD
.\data-extraction.exe --config .\config\config.yaml test-secret INTERNAL_AUDIT_DB_KEY
```

## 6. First-Run Validation

Run:

```powershell
.\data-extraction.exe --config .\config\config.yaml preflight
```

Expected result:

```text
Preflight status: passed
```

For `encryption: see`, preflight also validates that the SEE-enabled `sqlite3.dll` accepts `PRAGMA textkey`.

Then initialise the database:

```powershell
.\data-extraction.exe --config .\config\config.yaml init-db
```

## 7. Dry-Run Validation

Run:

```powershell
.\data-extraction.exe --config .\config\config.yaml run-dry-pipeline --reset-db
```

This uses fake source data and validates the local pipeline wiring.

## 8. Backfill Run

After source connectivity has been validated, run the initial backfill:

```powershell
.\data-extraction.exe --config .\config\config.yaml run-backfill
```

The backfill window is configured as 2 years.

## 9. Daily Run

Manual daily run:

```powershell
.\data-extraction.exe --config .\config\config.yaml run-daily
```

Daily extraction uses the previous calendar day.

## 10. Windows Task Scheduler

Create the daily scheduled task using:

```powershell
.\scripts\create_windows_task_example.ps1 `
  -BasePath "C:\InternalAuditDataExtraction" `
  -TaskName "Internal Audit Data Extraction - Daily" `
  -RunTime "02:00"
```

Client IT should configure the correct service account and permissions. The service account must be able to access the application folder, SQLite database, logs, Lotus Excel files, KeePass database, and KeePass key file. If fallback `keepass_cli` is used, it must also be able to run the wrapper script.

## 11. Logs And Monitoring

Main log file:

```text
logs\data_extraction.log
```

Tracking tables:

- `extraction_run`
- `extraction_job_run`
- `extraction_job_watermark`
- `extraction_error_log`
- `source_file_ingestion`
- `data_quality_check`

## 12. If Extraction Fails

Check:

- `logs\data_extraction.log`
- `extraction_run`
- `extraction_job_run`
- `extraction_error_log`

Common issues:

- Oracle connection failure
- KeePass database or key file is missing/inaccessible
- KeePass entry fields are incomplete
- Lotus Notes Excel file missing
- Invalid config path
- Network access blocked from VM
- DB file locked by another process
- SEE-enabled `sqlite3.dll` missing or copied to the wrong location

After fixing the issue, rerun:

```powershell
.\data-extraction.exe --config .\config\config.yaml run-daily
```

If the failure happened during initial load, rerun:

```powershell
.\data-extraction.exe --config .\config\config.yaml run-backfill
```

## 13. Known Pending Items

- Java CORBA Lotus Notes integration
- Final Power BI consumption pattern

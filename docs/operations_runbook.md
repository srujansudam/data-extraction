# Operations Runbook

## A. Overview

The data extraction service loads Internal Audit data from ORION, Flexcube, HRIS, and Lotus Notes into a local SQLite database for audit analytics and downstream consumption.

It supports:

- Daily runs using the previous calendar day window.
- Backfill runs using the configured backfill period.
- Direct source-to-final table jobs.
- Source-to-staging jobs followed by transform jobs for multi-source final tables.

Data is stored in the configured SQLite database path under `database.path`.

## B. Folder Structure On Client VM

Example:

```text
C:\InternalAuditDataExtraction\
  data-extraction.exe
  config\config.yaml
  data\
  logs\
  java\
  lotus_notes\incoming\
```

## C. Config File Maintenance

Update source secret references under:

```yaml
sources:
  orion:
    secret_ref: ORION_DB_PROD
  flexcube:
    secret_ref: FLEXCUBE_DB_PROD
  hris:
    secret_ref: HRIS_DB_PROD
```

Oracle endpoint details should live in Password Safe secret records, not in config. Lotus Excel file paths are configured under `sources.lotus_notes.files`.

Lotus mode is selected with:

```yaml
sources:
  lotus_notes:
    mode: excel # excel | corba
```

`corba` is reserved for future Java CORBA integration.

Secret provider selection:

```yaml
secrets:
  provider: environment # environment | password_safe_cli | password_safe_http
```

## D. Password Safe Setup

Current supported providers:

- `environment`: local development using environment variables or `.env`.
- `password_safe_cli`: production integration point via a client-provided Password Safe CLI.
- `password_safe_http`: placeholder until client API details are confirmed.

The CLI command template must return JSON:

```json
{
  "username": "...",
  "password": "...",
  "host": "...",
  "port": "1521",
  "service_name": "..."
}
```

Example config:

```yaml
secrets:
  provider: password_safe_cli
  password_safe_cli:
    executable_path: C:\PasswordSafe\password-safe.exe
    command_template: get-secret --ref {secret_ref}
```

Never store real credentials in config.

## E. Running Manually

```powershell
.\data-extraction.exe preflight
.\data-extraction.exe init-db
.\data-extraction.exe run-daily
.\data-extraction.exe run-backfill
.\data-extraction.exe run-dry-pipeline --reset-db
.\data-extraction.exe test-secret ORION_DB_PROD
```

`test-secret` logs only returned field names, never secret values.

## F. Failed Extraction Recovery

Check:

- `logs\data_extraction.log`
- `extraction_run`
- `extraction_job_run`
- `extraction_error_log`

For a failed daily run, fix the underlying cause and rerun `run-daily`. Use `run-backfill` when the historical window needs to be rebuilt or a schema/source issue affected multiple days.

If a Lotus Excel file is missing, place the expected file in the configured path and rerun. If Oracle connection fails, verify network access, Password Safe secret fields, service name, host, port, username, and password.

## G. Logs And Tracking Tables

- `extraction_run`: one row per pipeline run.
- `extraction_job_run`: one row per job execution.
- `extraction_job_watermark`: latest successful job window.
- `extraction_error_log`: run-level and job-level failures.
- `source_file_ingestion`: reserved for source file ingestion tracking.
- `data_quality_check`: reserved for quality checks.

## H. Lotus Notes Mode

Current mode is Excel ingestion. Required files:

- `lotus_bov_employees`
- `lotus_legal_rulings`
- `lotus_garnishee_orders`
- `lotus_poa_revocation`
- `lotus_discrepancies_management`

Replace Excel files at the configured paths before running the pipeline. Future Java CORBA mode will use:

```yaml
lotus_notes:
  mode: corba
```

## I. Packaging And Deployment

Build locally:

```powershell
.\scripts\build_exe.ps1
```

Copy:

- `data-extraction.exe`
- `config\config.yaml`
- `data\`
- `logs\`
- `java\lotus-corba-reader\` when CORBA is implemented

Do not copy local `.env`, development databases, local logs, or test files.

Run `preflight` on the VM before the first real run.

## J. Known Pending Items

- SQLCipher/SEE database encryption.
- Product-specific Password Safe integration.
- Java CORBA implementation.
- Power BI final consumption pattern.

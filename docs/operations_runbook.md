# Operations Runbook

## A. Overview

The data extraction service loads Internal Audit data from ORION, Flexcube, HRIS, and Lotus Notes into a local SQLite database for audit analytics and downstream consumption.

It supports:

- Daily runs using the previous calendar day window.
- Backfill runs using the configured backfill period.
- Direct source-to-final table jobs.
- Source-to-staging jobs followed by transform jobs for multi-source final tables.

Data is stored in the configured SQLite database path under `database.path`. Production uses SQLite SEE when `database.encryption: see`; see `docs/sqlite_see_setup.md`.

## B. Folder Structure On Client VM

Example:

```text
C:\InternalAuditDataExtraction\
  data-extraction.exe
  config\config.yaml
  data\
  logs\
  secrets\
    internal_audit_secrets.kdbx
    internal_audit_secrets.keyx
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

Oracle endpoint details should live in KeePass entries, not in config. Lotus Excel file paths are configured under `sources.lotus_notes.files`.

Lotus mode is selected with:

```yaml
sources:
  lotus_notes:
    mode: excel # excel | corba
```

Excel remains the default fallback. `corba` is a supported optional Phase 2 mode and should be enabled only after VM validation.

Secret provider selection:

```yaml
secrets:
  provider: environment # environment | keepass | keepass_cli
```

Production database encryption:

```yaml
database:
  encryption: see
  secret_ref: INTERNAL_AUDIT_DB_KEY
  see_activation_key: ""
```

`INTERNAL_AUDIT_DB_KEY` must return a secret field named `key`, `password`, `value`, or `secret`. Never store the DB key directly in config.

## D. KeePass Setup

Current supported providers:

- `environment`: local development using environment variables or `.env`.
- `keepass`: production provider that reads a local KeePass/KeePassXC `.kdbx` using PyKeePass.
- `keepass_cli`: fallback provider via a client-provided KeePass/KeePass-compatible CLI wrapper.

Recommended production config:

```yaml
secrets:
  provider: keepass
  keepass:
    database_path: secrets/internal_audit_secrets.kdbx
    key_file_path: secrets/internal_audit_secrets.keyx
    password_env_var: ""
```

Oracle entries should use the `secret_ref` as the KeePass entry title. Set UserName to the database username, Password to the database password, and custom fields:

- `host`
- `port`
- `service_name`

The SQLite SEE key entry should be titled `INTERNAL_AUDIT_DB_KEY`. Store the generated key as the entry password or as custom field `key`.

Fallback CLI mode must return JSON:

```json
{
  "username": "...",
  "password": "...",
  "host": "...",
  "port": "1521",
  "service_name": "..."
}
```

Fallback CLI example:

```yaml
secrets:
  provider: keepass_cli
  keepass_cli:
    executable_path: powershell.exe
    command_template: -NoProfile -ExecutionPolicy Bypass -File "C:\InternalAuditDataExtraction\scripts\get_keepass_secret.ps1" -SecretRef "{secret_ref}"
```

Never store real credentials in config.

## E. Running Manually

```powershell
.\data-extraction.exe preflight
.\data-extraction.exe diagnose-runtime
.\data-extraction.exe init-db
.\data-extraction.exe run-daily
.\data-extraction.exe run-backfill
.\data-extraction.exe run-dry-pipeline --reset-db
.\data-extraction.exe test-secret ORION_DB_PROD
.\data-extraction.exe test-source all
.\data-extraction.exe test-lotus-corba
.\data-extraction.exe extract-lotus-corba
```

`test-secret` logs only returned field names, never secret values.
`test-source` runs `SELECT 1 AS health_check FROM DUAL` and logs success or failure by source name only.
`diagnose-runtime` verifies that packaged runtime imports for `cryptography`,
`cffi`, and `oracledb` succeed. Oracle python-oracledb thin mode requires
`cryptography` in the executable.

## F. Failed Extraction Recovery

Check:

- `logs\data_extraction.log`
- `extraction_run`
- `extraction_job_run`
- `extraction_error_log`

For a failed daily run, fix the underlying cause and rerun `run-daily`. Use `run-backfill` when the historical window needs to be rebuilt or a schema/source issue affected multiple days.

If a Lotus Excel file is missing, place the expected file in the configured path and rerun. If Oracle connection fails, verify network access, KeePass entry fields, service name, host, port, username, and password.

If Oracle source testing fails with `python-oracledb thin mode cannot be used
because the cryptography package cannot be imported`, rebuild the executable
with the current PyInstaller spec so `cryptography` and `cffi` are bundled, then
rerun `diagnose-runtime` and `test-source all`.

## G. Logs And Tracking Tables

- `extraction_run`: one row per pipeline run.
- `extraction_job_run`: one row per job execution.
- `extraction_job_watermark`: latest successful job window.
- `extraction_error_log`: run-level and job-level failures.
- `source_file_ingestion`: reserved for source file ingestion tracking.
- `data_quality_check`: reserved for quality checks.

Application logs are written to the configured `logging.folder` as
`data_extraction.log`. The file rotates by size at 10 MB and keeps up to 30
backup files. Console logging remains enabled for manual runs. Logs include run,
job, source, target table, duration, row counts, and sanitized exception
messages. Secret values and credential-bearing connection strings must not be
logged.

## H. Lotus Notes Mode

Current mode is Excel ingestion. Required files:

- `lotus_bov_employees`
- `lotus_legal_rulings`
- `lotus_garnishee_orders`
- `lotus_poa_revocation`
- `lotus_discrepancies_management`

Replace Excel files at the configured paths before running the pipeline. Optional Phase 2 CORBA uses:

```yaml
lotus_notes:
  mode: corba
```

CORBA prerequisites:

- Java 8 runtime, preferably client-approved IBM Semeru/OpenJ9 8
- `notes.jar` and `ncso.jar` supplied by BOV/client
- `diiop_ior.txt` supplied by BOV/client
- network access to `10.64.100.15:63148`
- `LOTUS_NOTES_PROD` KeePass entry
- read access to all five configured NSF databases and EY views

Run `test-lotus-corba` before `extract-lotus-corba`. The test command validates files, Java, config, and credentials without connecting to Domino.

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
- `secrets\`
- `scripts\get_keepass_secret.ps1` only for `keepass_cli` fallback

Do not copy local `.env`, development databases, local logs, test files, KeePass database files, KeePass master passwords, or key files.

Run `preflight` on the VM before the first real run. Preflight validates that SEE accepts `PRAGMA textkey` when encryption is enabled. A failure usually means the app is using normal SQLite instead of a SEE-enabled `sqlite3.dll`, or the DB key/activation key is wrong.

## J. Known Pending Items

- Java CORBA requires BOV/client runtime validation before enablement.
- Power BI final consumption pattern.

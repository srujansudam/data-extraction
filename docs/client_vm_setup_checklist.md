# Client VM Setup Checklist

## 1. Objective

This checklist is used to deploy the Internal Audit Data Extraction application on the client-provided Windows VM.

The application extracts data from ORION, Flexcube, HRIS, and Lotus Notes Excel extracts, loads the internal SQLite database, and tracks extraction runs, job status, errors, and data quality checks.

## 2. Target folder structure

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
  java\
    lotus-corba-reader\

Create the folder structure using:

.\scripts\setup_client_vm_folders.ps1 -BasePath "C:\InternalAuditDataExtraction"
3. Files to copy

Copy these files to the VM:

data-extraction.exe
config\config.yaml

If Lotus Notes is in Excel mode, place the latest Excel extracts under:

C:\InternalAuditDataExtraction\lotus_notes\incoming\

Expected Lotus Notes files should map to the config keys:

lotus_bov_employees
lotus_legal_rulings
lotus_garnishee_orders
lotus_poa_revocation
lotus_discrepancies_management
4. Config setup

The production config should be created from config.example.yaml.

The config should contain:

database path
logging folder
source enablement flags
Password Safe provider type
Password Safe secret references
Lotus Notes mode and file paths

Do not store real passwords in the config file.

5. Password Safe setup

Production should use the configured Password Safe provider.

For CLI-based Password Safe integration, the command must return JSON in this shape:

{
  "username": "...",
  "password": "...",
  "host": "...",
  "port": "1521",
  "service_name": "..."
}

The application will only log returned secret keys, never secret values.

Test each secret reference:

.\data-extraction.exe test-secret ORION_DB_PROD --config .\config\config.yaml
.\data-extraction.exe test-secret FLEXCUBE_DB_PROD --config .\config\config.yaml
.\data-extraction.exe test-secret HRIS_DB_PROD --config .\config\config.yaml
6. First-run validation

Run:

.\data-extraction.exe preflight --config .\config\config.yaml

Expected result:

Preflight status: passed

Then initialise the database:

.\data-extraction.exe init-db --config .\config\config.yaml
7. Dry-run validation

Run:

.\data-extraction.exe run-dry-pipeline --reset-db --config .\config\config.yaml

This uses fake source data and validates the full local pipeline.

8. Backfill run

After source connectivity has been validated, run the initial backfill:

.\data-extraction.exe run-backfill --config .\config\config.yaml

The backfill window is configured as 2 years.

9. Daily run

Manual daily run:

.\data-extraction.exe run-daily --config .\config\config.yaml

Daily extraction uses the previous calendar day.

10. Windows Task Scheduler

Create the daily scheduled task using:

.\scripts\create_windows_task_example.ps1 `
  -BasePath "C:\InternalAuditDataExtraction" `
  -TaskName "Internal Audit Data Extraction - Daily" `
  -RunTime "02:00"

Client IT should configure the correct service account and permissions.

11. Logs and monitoring

Main log file:

logs\data_extraction.log

Tracking tables:

extraction_run
extraction_job_run
extraction_job_watermark
extraction_error_log
source_file_ingestion
data_quality_check
12. If extraction fails

Check:

logs\data_extraction.log
extraction_run
extraction_job_run
extraction_error_log

Common issues:

Oracle connection failure
Password Safe secret not returned
Lotus Notes Excel file missing
Invalid config path
Network access blocked from VM
DB file locked by another process

After fixing the issue, rerun:

.\data-extraction.exe run-daily --config .\config\config.yaml

If the failure happened during initial load, rerun:

.\data-extraction.exe run-backfill --config .\config\config.yaml
13. Known pending items
SQLite encryption decision: SQLCipher or SQLite SEE
Java CORBA Lotus Notes integration
Final Power BI consumption pattern
Client-specific Password Safe CLI/API details
# Developer Guide

## Architecture

The service is split into these layers:

- `connectors/`: source-system connection clients.
- `secrets/`: secret-provider abstractions.
- `db/`: database adapter and schema.
- `jobs/extract/`: direct source-to-final extraction jobs.
- `jobs/staging/`: source-to-staging extraction jobs.
- `staging/`: generic staging table reader/writer helpers.
- `transform/`: staging-to-final transform jobs.
- `pipeline/`: job building and run orchestration.
- `dev/`: local dry-run helpers only.

## Add A Direct Extraction Job

1. Add a file under `src/data_extraction/jobs/extract/`.
2. Subclass `BaseExtractionJob`.
3. Use `SourceQueryClient`, not a concrete connector.
4. Add idempotent load behavior.
5. Register the job in `jobs/registry.py` and `jobs/factory.py`.
6. Add focused tests with a fake source client.

## Add A Staging Extraction Job

Use `OracleToStagingJob` for source queries or `ExcelToStagingJob` for Excel input. Add source-specific classes under `jobs/staging/`.

`jobs/staging/` contains job definitions. `staging/` contains generic staging infrastructure such as `StagingWriter` and `StagingReader`.

## Add A Transform Job

1. Add a file under `src/data_extraction/transform/`.
2. Subclass `BaseTransformJob`.
3. Read current `run_id` rows using `StagingReader` where possible.
4. Write to final model tables using the database adapter.
5. Add the job to `transform/factory.py` and pipeline definitions when appropriate.
6. Add tests that stage JSON payload rows and verify final-table output.

## Testing With FakeSourceClient

Tests should use fake clients that implement:

```python
def query_all(sql: str, params=None) -> list[dict[str, object]]:
    return [...]
```

Do not connect to Oracle, HRIS, Lotus Notes, Password Safe, or external services in unit tests.

## Run Tests And Ruff

```powershell
ruff check .
pytest
```

In constrained local runtimes, use the project virtual environment or append installed project dependencies as needed.

## Packaging

```powershell
.\scripts\build_exe.ps1
```

The package should not include real config, secrets, local database files, or logs.

## Credentials

Never hardcode credentials. Use secret references in config and resolve them through `create_secret_provider(settings)`.

## Schema Changes

Keep schema changes in `src/data_extraction/db/schema.py`. Add tests that create the schema and verify tables/columns. Avoid destructive migrations until a migration strategy is defined.

## Data Model Safety

For final-table changes, update:

- schema
- extraction or transform job
- factory/registry if needed
- tests
- docs when behavior changes

Keep business SQL aligned to the scenario SQL document and the data model reference.

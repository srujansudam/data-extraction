# Deployment

## Build The Executable

From a development machine with the project dependencies installed:

```powershell
.\scripts\build_exe.ps1
```

The script runs `pytest`, runs `ruff check .`, then builds `dist\data-extraction.exe` with PyInstaller. It does not package real config files, secrets, SQLite database files, or logs.

## Files To Copy To The Client VM

Copy these deployment assets:

- `data-extraction.exe`
- `config/config.yaml`
- `data/`
- `logs/`
- `java/lotus-corba-reader/` if CORBA is enabled later

The client VM should not need Python libraries installed separately.

## Current Limitations

- SQLite encryption decision is pending: SQLCipher or SQLite SEE.
- Password Safe provider is pending client product/API details.
- Lotus Notes currently supports Excel ingestion. CORBA integration will be added later.

## Commands

```powershell
.\data-extraction.exe preflight
.\data-extraction.exe init-db
.\data-extraction.exe run-dry-pipeline --reset-db
.\data-extraction.exe run-daily
.\data-extraction.exe run-backfill
```

Use `--config path\to\config.yaml` when the config is not in the default location.

## Credentials

Do not store real credentials in config files. Production config should contain secret references only. The actual secret provider integration can then resolve those references at runtime.

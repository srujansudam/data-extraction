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
- SEE-enabled `sqlite3.dll` beside `data-extraction.exe` when `database.encryption: see`
- `scripts/get_keepass_secret.ps1` after client-specific KeePass wiring
- `java/lotus-corba-reader/` if CORBA is enabled later

The client VM should not need Python libraries installed separately.

## Current Limitations

- SQLite SEE is the production encryption option. SEE binaries and license material are not included in this repository.
- Production secrets use a local KeePass/KeePass-compatible CLI wrapper selected by `secrets.provider: keepass_cli`.
- Lotus Notes currently supports Excel ingestion. CORBA integration will be added later.

For production encryption setup, follow [sqlite_see_setup.md](sqlite_see_setup.md).
For KeePass setup, follow [keepass_setup.md](keepass_setup.md).

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

Do not store real credentials in config files. Production config should contain secret references only. The configured KeePass wrapper resolves those references at runtime.

For encrypted production databases, `database.secret_ref` should point to `INTERNAL_AUDIT_DB_KEY`, and that secret should return JSON such as `{"key": "long-random-passphrase"}`.

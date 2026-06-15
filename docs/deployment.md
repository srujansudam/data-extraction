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
- `secrets/` containing the client-created `.kdbx` and `.keyx` files
- SEE-enabled `sqlite3.dll` beside `data-extraction.exe` when `database.encryption: see`
- `scripts/get_keepass_secret.ps1` only if using the fallback `keepass_cli` provider
- `java/lotus-corba-reader/` source or built reader jar when CORBA is enabled
- client-supplied Java 8 runtime, `notes.jar`, `ncso.jar`, and `diiop_ior.txt` for CORBA

The client VM should not need Python libraries installed separately.

## Current Limitations

- SQLite SEE is the production encryption option. SEE binaries and license material are not included in this repository.
- Production secrets use a local KeePass/KeePassXC `.kdbx` database selected by `secrets.provider: keepass`.
- Lotus Notes defaults to Excel ingestion. Java 8 CORBA is a supported optional Phase 2 mode.

For production encryption setup, follow [sqlite_see_setup.md](sqlite_see_setup.md).
For KeePass setup, follow [keepass_setup.md](keepass_setup.md).

## Commands

```powershell
.\data-extraction.exe preflight
.\data-extraction.exe test-secret ORION_DB_PROD
.\data-extraction.exe test-source all
.\data-extraction.exe test-lotus-corba
.\data-extraction.exe init-db
.\data-extraction.exe run-dry-pipeline --reset-db
.\data-extraction.exe run-daily
.\data-extraction.exe run-backfill
```

Use `--config path\to\config.yaml` when the config is not in the default location.

Create `config/config.yaml` from the production template. Only `config.yaml` should be edited for deployment-specific source references, paths, Lotus filenames, and optional SEE activation configuration.

For CORBA, do not commit or bundle the real Domino jars or IOR file. BOV/client IT must place them at the configured VM paths and provide network access to `10.64.100.15:63148`.

## Credentials

Do not store real credentials in config files. Production config should contain secret references only. The direct KeePass provider resolves those references from the local `.kdbx` at runtime.

For encrypted production databases, `database.secret_ref` should point to `INTERNAL_AUDIT_DB_KEY`, and that secret should return JSON such as `{"key": "long-random-passphrase"}`.

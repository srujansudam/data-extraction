# Deployment

## Build The Executable

From a development machine with the project dependencies installed:

```powershell
.\scripts\build_exe.ps1
```

The script runs `pytest`, runs `ruff check .`, then builds `dist\data-extraction.exe` with PyInstaller. It does not package real config files, secrets, SQLite database files, or logs.

The PyInstaller spec explicitly bundles `cryptography`, `cffi`, and
`oracledb` support modules. Oracle python-oracledb thin mode requires
`cryptography` at runtime. If a VM reports:

```text
python-oracledb thin mode cannot be used because the cryptography package cannot be imported
```

rebuild the executable from a clean `build\` and `dist\` using
`.\scripts\build_exe.ps1`, then recreate the release bundle.

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
- HRIS is configured as a Dynamics 365 / Dataverse API source in production. The client secret is resolved from `HRIS_D365_PROD`; tenant ID, client ID, scope, token URL, health check URL, and endpoint mappings are configured in `config.yaml`.
- Lotus Notes can be disabled while BOV IT resolves access. When disabled, preflight and run summaries show `SKIPPED (disabled)` and Lotus-derived tables remain empty. When enabled, Excel ingestion is the fallback mode; Java 8 CORBA is a supported optional Phase 2 mode.

For production encryption setup, follow [sqlite_see_setup.md](sqlite_see_setup.md).
For KeePass setup, follow [keepass_setup.md](keepass_setup.md).

## Commands

```powershell
.\data-extraction.exe preflight
.\data-extraction.exe diagnose-runtime
.\data-extraction.exe test-secret ORION_DB_PROD
.\data-extraction.exe test-secret HRIS_D365_PROD
.\data-extraction.exe test-source all
.\data-extraction.exe test-lotus-corba
.\data-extraction.exe init-db
.\data-extraction.exe run-dry-pipeline --reset-db
.\data-extraction.exe run-daily
.\data-extraction.exe run-backfill
```

Use `--config path\to\config.yaml` when the config is not in the default location.

Create `config/config.yaml` from the production template. Only `config.yaml` should be edited for deployment-specific source references, paths, Lotus enablement/filenames, and optional SEE activation configuration. For the current deployment, keep `sources.lotus_notes.enabled: false` until Lotus connectivity is ready.

For CORBA, do not commit or bundle the real Domino jars or IOR file. BOV/client IT must place them at the configured VM paths and provide network access to `10.64.100.15:63148`.

## Credentials

Do not store real credentials in config files. Production config should contain secret references only. The direct KeePass provider resolves those references from the local `.kdbx` at runtime.

For encrypted production databases, `database.secret_ref` should point to `INTERNAL_AUDIT_DB_KEY`, and that secret should return JSON such as `{"key": "long-random-passphrase"}`.

For HRIS Dynamics 365, `sources.hris.dynamics365.secret_ref` should point to `HRIS_D365_PROD`, and that KeePass entry should store the Dataverse application client secret as the entry password or a supported field (`client_secret`, `secret`, or `value`). Bearer tokens and client secrets must never be logged or stored in config.

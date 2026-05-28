# SQLite SEE Setup

## A. Overview

SQLite SEE is used to encrypt the local Internal Audit SQLite database on the client VM. Local development remains `database.encryption: none`; production should use `database.encryption: see`.

The application expects a SEE-enabled SQLite runtime. Normal Python `sqlite3` does not automatically use SEE. The application keys the database immediately after opening it using `PRAGMA textkey` and fails fast if SEE is not active or the key is not accepted.

## B. What Must Be Obtained From Client/Licensing

The licensed client must provide:

- SQLite SEE source code access.
- The selected SEE source variant.
- SEE activation key, if the selected build requires activation.
- Approval for where the database key will be stored and recovered.

Do not commit SEE source code, SEE binaries, activation keys, or database keys to this repository.

## C. Recommended SEE Variant

For new development, use `sqlite3-see-aes256-ofb.c` unless the client security architecture prefers another variant.

The `cryptoapi` variant may be considered if the client specifically wants Windows CryptoAPI integration.

## D. Build Prerequisites On Windows

Install Visual Studio Build Tools, the Desktop development with C++ workload, and the Windows SDK. Build from the `x64 Native Tools Command Prompt for VS`.

## E. Compile SEE sqlite3.dll

Use the variant file selected by the client:

```cmd
cd C:\path\to\sqlite-see-source
cl -DSQLITE_API=__declspec(dllexport) sqlite3-see-aes256-ofb.c /link /dll /out:sqlite3.dll
```

Compile the SEE shell:

```cmd
cl /Fesqlite3-see.exe shell.c sqlite3-see-aes256-ofb.c
```

## F. Where To Place sqlite3.dll

Copy the SEE-enabled `sqlite3.dll` beside `data-extraction.exe` in the release folder. If PyInstaller produces an internal folder containing another `sqlite3.dll`, replace that DLL too.

The practical test is whether preflight accepts `PRAGMA textkey` when `database.encryption: see`.

## G. Generate And Store DB Key

Generate a long random key on the VM:

```powershell
$keyBytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Fill($keyBytes)
$key = [Convert]::ToBase64String($keyBytes)
$key
```

Store this key in the configured secret provider as:

```json
{"key": "<generated-key>"}
```

Use secret reference `INTERNAL_AUDIT_DB_KEY`. Do not put the key in `config.yaml`. Restrict key access to the service account and administrators.

## H. Configure config.yaml

```yaml
database:
  type: sqlite
  path: data/internal_audit.db
  encryption: see
  secret_ref: INTERNAL_AUDIT_DB_KEY
  see_activation_key: ""
```

Set `see_activation_key` only if required by the SEE build. Never commit `config.yaml`.

## I. First Encrypted DB Initialisation

Delete old unencrypted files before first encrypted initialisation:

```powershell
Remove-Item .\data\internal_audit.db, .\data\internal_audit.db-wal, .\data\internal_audit.db-shm -ErrorAction SilentlyContinue
.\data-extraction.exe --config .\config\config.yaml preflight
.\data-extraction.exe --config .\config\config.yaml init-db
```

## J. Verify Encryption

Use the SEE shell:

```powershell
.\sqlite3-see.exe -textkey "<key>" .\data\internal_audit.db ".tables"
```

Wrong key should fail:

```powershell
.\sqlite3-see.exe -textkey "wrong-key" .\data\internal_audit.db ".tables"
```

Normal SQLite without SEE/key should fail or report an unreadable database.

## K. Key Maintenance

The client must define who owns the database key and where recovery material is stored. Backups must include both encrypted database files and the process and authority to recover the key.

If the key is lost, the database cannot be recovered.

Key rotation approach:

1. Take a full backup.
2. Create a new encrypted DB with a new key.
3. Export/import data or rerun backfill if acceptable.
4. Validate the new DB.
5. Retire the old DB securely.

Do not rotate casually during daily operations.

## L. Troubleshooting

Error: `SQLite SEE key was not accepted.`

Possible causes:

- App is using normal `sqlite3.dll`.
- `sqlite3.dll` was copied to the wrong location.
- Activation key is missing or wrong.
- DB key is missing or wrong.

Error: `file is encrypted or is not a database`.

Possible causes:

- Wrong key.
- Encrypted DB opened with normal SQLite.

Error: `no such table` after init.

Possible causes:

- Wrong DB path.
- `init-db` was not run.

WAL/SHM note: remove `db`, `db-wal`, and `db-shm` together when resetting.

## M. Security Notes

- Do not log the DB key.
- Do not email the DB key.
- Do not store the key in config.
- Restrict DB and secret files with NTFS ACLs.
- Ensure the scheduled task account can access the key and DB folder.
- Client backup process must protect both the encrypted DB and key recovery path.

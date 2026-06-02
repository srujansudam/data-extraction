# KeePass Secret Setup

## A. Overview

Production secrets are resolved through a local KeePass or KeePass-compatible vault using a CLI/wrapper contract.

The application does not read a KeePass database directly. It calls the configured wrapper command with a `secret_ref`, and the wrapper writes a JSON object to stdout. The application parses that JSON and uses only the returned keys and values in memory.

Local development can continue to use:

```yaml
secrets:
  provider: environment
```

Production should use:

```yaml
secrets:
  provider: keepass_cli
```

## B. Supported Provider

Current supported production provider:

- `keepass_cli`

The provider accepts:

- `executable_path`: the executable to run, usually `powershell.exe`.
- `command_template`: arguments passed to that executable. It must contain `{secret_ref}`.

Example:

```yaml
secrets:
  provider: keepass_cli
  keepass_cli:
    executable_path: powershell.exe
    command_template: -NoProfile -ExecutionPolicy Bypass -File "C:\InternalAuditDataExtraction\scripts\get_keepass_secret.ps1" -SecretRef "{secret_ref}"
```

## C. Wrapper Contract

The wrapper receives a secret reference and must print one JSON object to stdout.

Input example:

```powershell
.\scripts\get_keepass_secret.ps1 -SecretRef ORION_DB_PROD
```

Oracle secret output:

```json
{
  "username": "...",
  "password": "...",
  "host": "...",
  "port": "1521",
  "service_name": "..."
}
```

SQLite SEE key output:

```json
{
  "key": "long-random-passphrase"
}
```

The wrapper must not print secret values to logs, stderr, progress messages, or diagnostic output.

## D. KeePass Database Setup

Create a client-controlled KeePass database on the VM or in a secured location approved by client IT.

Recommended entries:

- `ORION_DB_PROD`
- `FLEXCUBE_DB_PROD`
- `HRIS_DB_PROD`
- `INTERNAL_AUDIT_DB_KEY`

Each Oracle source entry must provide fields that the wrapper can convert to the required JSON keys:

- `username`
- `password`
- `host`
- `port`
- `service_name`

The SEE database key entry must return one of:

- `key`
- `password`
- `value`
- `secret`

Use `key` for clarity.

## E. Wrapper Script

The release bundle includes:

- `scripts\get_keepass_secret.ps1`
- `scripts\README_keepass_setup.md`

The PowerShell script is a template. Client IT should edit it on the VM to call the approved local KeePass tool, such as KeePassXC CLI, KeePass/KPScript, or another KeePass-compatible wrapper.

The script should:

- accept `-SecretRef`
- retrieve only the requested entry
- map fields into the required JSON shape
- write only JSON to stdout
- avoid logging secret values
- fail clearly when the reference is missing

## F. Testing

Run preflight:

```powershell
.\data-extraction.exe --config .\config\config.yaml preflight
```

Test a source secret:

```powershell
.\data-extraction.exe --config .\config\config.yaml test-secret ORION_DB_PROD
```

Test the SQLite SEE database key:

```powershell
.\data-extraction.exe --config .\config\config.yaml test-secret INTERNAL_AUDIT_DB_KEY
```

`test-secret` logs only field names, never field values.

## G. Maintenance And Security

- Do not store `.kdbx` files in the repository.
- Do not store real credentials in `config.yaml`.
- Do not copy KeePass master passwords or key files into the release bundle.
- Restrict KeePass database, key file, config, data, and logs with NTFS ACLs.
- Ensure the scheduled task service account can access the wrapper, KeePass database, and any key file it needs.
- Back up the KeePass database and recovery material using the client-approved process.
- If the `INTERNAL_AUDIT_DB_KEY` entry is lost, the encrypted SQLite SEE database cannot be recovered.

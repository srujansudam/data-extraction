# KeePass Secret Setup

## A. Overview

Production secrets are resolved from a local KeePass/KeePassXC `.kdbx` database on the client VM. The packaged application reads the vault directly at runtime using PyKeePass.

Local development can continue to use:

```yaml
secrets:
  provider: environment
```

Production should use:

```yaml
secrets:
  provider: keepass
```

The older `keepass_cli` wrapper remains available as a fallback for clients who prefer an external KeePass CLI integration, but it is no longer the recommended path.

## B. Recommended VM Structure

```text
C:\InternalAuditDataExtraction\
  data-extraction.exe
  config\
    config.yaml
  data\
  logs\
  secrets\
    internal_audit_secrets.kdbx
    internal_audit_secrets.keyx
  lotus_notes\
    incoming\
```

Do not commit or bundle real `.kdbx`, `.keyx`, passwords, DB keys, or credentials.

## C. Config

Recommended production configuration:

```yaml
secrets:
  provider: keepass

  keepass:
    database_path: secrets/internal_audit_secrets.kdbx
    key_file_path: secrets/internal_audit_secrets.keyx
    password_env_var: ""
```

`database_path` is required.

For unattended scheduled-task execution, the recommended unlock method is a key file protected by NTFS ACLs. If a master password is also required, use `password_env_var` only when client IT approves secure environment-variable management.

Fallback CLI configuration, if needed:

```yaml
secrets:
  provider: keepass_cli
  keepass_cli:
    executable_path: powershell.exe
    command_template: -NoProfile -ExecutionPolicy Bypass -File "C:\InternalAuditDataExtraction\scripts\get_keepass_secret.ps1" -SecretRef "{secret_ref}"
```

## D. KeePass Entries

Recommended entries:

- `ORION_DB_PROD`
- `FLEXCUBE_DB_PROD`
- `HRIS_DB_PROD`
- `INTERNAL_AUDIT_DB_KEY`

The entry title must match the configured `secret_ref`.

Oracle source entries:

- Title: `ORION_DB_PROD`, `FLEXCUBE_DB_PROD`, or `HRIS_DB_PROD`
- UserName: database username
- Password: database password
- Custom fields:
  - `host`
  - `port`
  - `service_name`

SQLite SEE database key entry:

- Title: `INTERNAL_AUDIT_DB_KEY`
- Password: generated long random DB key
- Optional custom field:
  - `key`

If `INTERNAL_AUDIT_DB_KEY` has no custom `key` field, the application returns the entry password as `{"key": "<password>"}`.

## E. Generate The SEE DB Key

Generate a long random key on the VM:

```powershell
$keyBytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Fill($keyBytes)
$key = [Convert]::ToBase64String($keyBytes)
$key
```

Store it in the KeePass entry titled `INTERNAL_AUDIT_DB_KEY`. Do not put the key in `config.yaml`.

## F. Unattended Execution

The scheduled task should run under a Windows account that can read:

- `secrets\internal_audit_secrets.kdbx`
- `secrets\internal_audit_secrets.keyx`
- `config\config.yaml`
- `data\`
- `logs\`
- Lotus Excel input folder

Use NTFS ACLs to restrict the KeePass database and key file to the service account and administrators.

Do not store a master password in `config.yaml`. If a password is required, store the environment variable using a client-approved secure process and configure:

```yaml
secrets:
  keepass:
    password_env_var: INTERNAL_AUDIT_KEEPASS_PASSWORD
```

## G. Testing

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

## H. Maintenance And Security

- Do not store `.kdbx` files in the repository.
- Do not store `.keyx` files in the repository.
- Do not store real credentials in `config.yaml`.
- Do not copy KeePass master passwords or key files into source control.
- Back up the KeePass database and key file using the client-approved process.
- If the `INTERNAL_AUDIT_DB_KEY` entry is lost, the encrypted SQLite SEE database cannot be recovered.
- Rotate the SEE database key only with a planned backup, re-encryption, validation, and rollback process.

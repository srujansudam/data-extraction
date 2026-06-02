# KeePass Wrapper Setup

`get_keepass_secret.ps1` is a template wrapper for production secret retrieval.
The application calls it through:

```yaml
secrets:
  provider: keepass_cli
  keepass_cli:
    executable_path: powershell.exe
    command_template: -NoProfile -ExecutionPolicy Bypass -File "C:\InternalAuditDataExtraction\scripts\get_keepass_secret.ps1" -SecretRef "{secret_ref}"
```

The wrapper must write exactly one JSON object to stdout and must never print
secret values to logs or stderr.

Oracle source secrets should return:

```json
{
  "username": "...",
  "password": "...",
  "host": "...",
  "port": "1521",
  "service_name": "..."
}
```

SQLite SEE database key secrets should return:

```json
{
  "key": "long-random-passphrase"
}
```

Do not place `.kdbx` files, master passwords, key files, or real credentials in
the repository or release bundle. Configure those only on the client VM with
client-approved file permissions.

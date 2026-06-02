param(
    [Parameter(Mandatory = $true)]
    [string]$SecretRef,

    [string]$KeePassDatabasePath = "",
    [string]$KeePassCliPath = "",
    [string]$KeyFilePath = ""
)

$ErrorActionPreference = "Stop"

<#
KeePass/KeePass-compatible secret wrapper template.

Contract expected by data-extraction:
- Input: -SecretRef "ORION_DB_PROD"
- Stdout: one JSON object containing secret fields
- Stderr/logs: never print secret values

Example JSON shapes:
  Oracle source secret:
    {"username":"...","password":"...","host":"...","port":"1521","service_name":"..."}

  SQLite SEE database key:
    {"key":"long-random-passphrase"}

This template intentionally does not contain real KeePass database paths, master
passwords, key files, or client-specific CLI commands.
#>

if ([string]::IsNullOrWhiteSpace($SecretRef)) {
    throw "SecretRef is required."
}

# TODO: Configure one of the client-approved local retrieval methods below.
#
# Option A: KeePassXC CLI pattern, if approved by client IT.
# $args = @("show", "--attributes", "UserName,Password,URL,Notes", $KeePassDatabasePath, $SecretRef)
# if (-not [string]::IsNullOrWhiteSpace($KeyFilePath)) {
#     $args = @("--key-file", $KeyFilePath) + $args
# }
# $raw = & $KeePassCliPath @args
# Convert $raw into the required JSON object and Write-Output it.
#
# Option B: KeePass/KPScript pattern, if approved by client IT.
# $raw = & $KeePassCliPath "-c:GetEntryString" $KeePassDatabasePath "-ref-Title:$SecretRef" "-Field:Password"
# Convert retrieved fields into the required JSON object and Write-Output it.

throw "KeePass wrapper is not configured. Edit scripts\get_keepass_secret.ps1 to call the client-approved KeePass CLI for SecretRef '$SecretRef'."

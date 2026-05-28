param(
    [string]$ReleaseRoot = "dist\release",
    [string]$AppFolderName = "InternalAuditDataExtraction"
)

$ErrorActionPreference = "Stop"

$ExePath = "dist\data-extraction.exe"
$ReleasePath = Join-Path $ReleaseRoot $AppFolderName

Write-Host "Creating release bundle..."
Write-Host "Release path: $ReleasePath"

if (-not (Test-Path $ExePath)) {
    throw "Executable not found at $ExePath. Run .\scripts\build_exe.ps1 first."
}

if (Test-Path $ReleasePath) {
    Write-Host "Removing existing release folder..."
    Remove-Item $ReleasePath -Recurse -Force
}

New-Item -Path $ReleasePath -ItemType Directory | Out-Null
New-Item -Path "$ReleasePath\config" -ItemType Directory | Out-Null
New-Item -Path "$ReleasePath\data" -ItemType Directory | Out-Null
New-Item -Path "$ReleasePath\logs" -ItemType Directory | Out-Null
New-Item -Path "$ReleasePath\lotus_notes\incoming" -ItemType Directory -Force | Out-Null
New-Item -Path "$ReleasePath\java\lotus-corba-reader" -ItemType Directory -Force | Out-Null
New-Item -Path "$ReleasePath\docs" -ItemType Directory | Out-Null
New-Item -Path "$ReleasePath\scripts" -ItemType Directory | Out-Null
New-Item -Path "$ReleasePath\tools\sqlite-see" -ItemType Directory -Force | Out-Null

Copy-Item $ExePath "$ReleasePath\data-extraction.exe"

Copy-Item "config\config.example.yaml" "$ReleasePath\config\config.example.yaml"
Copy-Item "config\config.production.template.yaml" "$ReleasePath\config\config.production.template.yaml"

Copy-Item "docs\deployment.md" "$ReleasePath\docs\deployment.md" -ErrorAction SilentlyContinue
Copy-Item "docs\operations_runbook.md" "$ReleasePath\docs\operations_runbook.md" -ErrorAction SilentlyContinue
Copy-Item "docs\developer_guide.md" "$ReleasePath\docs\developer_guide.md" -ErrorAction SilentlyContinue
Copy-Item "docs\client_vm_setup_checklist.md" "$ReleasePath\docs\client_vm_setup_checklist.md" -ErrorAction SilentlyContinue
Copy-Item "docs\sqlite_see_setup.md" "$ReleasePath\docs\sqlite_see_setup.md" -ErrorAction SilentlyContinue

Copy-Item "scripts\setup_client_vm_folders.ps1" "$ReleasePath\scripts\setup_client_vm_folders.ps1"
Copy-Item "scripts\create_windows_task_example.ps1" "$ReleasePath\scripts\create_windows_task_example.ps1"
Copy-Item "tools\sqlite-see\README.md" "$ReleasePath\tools\sqlite-see\README.md" -ErrorAction SilentlyContinue

@"
Internal Audit Data Extraction Release Bundle

Next steps on client VM:
1. Copy config\config.production.template.yaml to config\config.yaml.
2. Keep database.encryption: see for production.
3. Configure INTERNAL_AUDIT_DB_KEY in the configured secret provider. It must return JSON like {"key":"long-random-passphrase"}.
4. Compile/copy the licensed SEE-enabled sqlite3.dll beside data-extraction.exe before running an encrypted DB.
5. Update config\config.yaml with Password Safe secret references and Lotus Excel file paths.
6. Place Lotus Notes Excel extracts under lotus_notes\incoming.
7. Run:
   .\data-extraction.exe --config .\config\config.yaml preflight
8. Test secrets:
   .\data-extraction.exe --config .\config\config.yaml test-secret ORION_DB_PROD 
   .\data-extraction.exe --config .\config\config.yaml test-secret FLEXCUBE_DB_PROD 
   .\data-extraction.exe --config .\config\config.yaml test-secret HRIS_DB_PROD 
9. Run initial backfill:
   .\data-extraction.exe --config .\config\config.yaml run-backfill
10. Schedule daily run:
   .\data-extraction.exe --config .\config\config.yaml run-daily

SEE binaries, SEE source code, activation keys, and database keys are not included in this release bundle. See docs\sqlite_see_setup.md.
"@ | Out-File "$ReleasePath\README_RELEASE.txt" -Encoding utf8

Write-Host ""
Write-Host "Release bundle created successfully."
Write-Host "Location: $ReleasePath"
Write-Host ""
Write-Host "Contents:"
Get-ChildItem $ReleasePath -Recurse | Select-Object FullName

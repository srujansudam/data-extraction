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
New-Item -Path "$ReleasePath\secrets" -ItemType Directory | Out-Null
New-Item -Path "$ReleasePath\lotus_notes\incoming" -ItemType Directory -Force | Out-Null
New-Item -Path "$ReleasePath\data\lotus_notes\corba_output" -ItemType Directory -Force | Out-Null
New-Item -Path "$ReleasePath\java\lotus-corba-reader" -ItemType Directory -Force | Out-Null
New-Item -Path "$ReleasePath\java\lib" -ItemType Directory -Force | Out-Null
New-Item -Path "$ReleasePath\docs" -ItemType Directory | Out-Null
New-Item -Path "$ReleasePath\scripts" -ItemType Directory | Out-Null
New-Item -Path "$ReleasePath\tools\sqlite-see" -ItemType Directory -Force | Out-Null

Copy-Item $ExePath "$ReleasePath\data-extraction.exe"

Copy-Item "config\config.example.yaml" "$ReleasePath\config\config.example.yaml"
Copy-Item "config\config.production.template.yaml" "$ReleasePath\config\config.production.template.yaml"
Copy-Item "config\README_diiop_ior.txt" "$ReleasePath\config\README_diiop_ior.txt"

Copy-Item "docs\deployment.md" "$ReleasePath\docs\deployment.md" -ErrorAction SilentlyContinue
Copy-Item "docs\operations_runbook.md" "$ReleasePath\docs\operations_runbook.md" -ErrorAction SilentlyContinue
Copy-Item "docs\developer_guide.md" "$ReleasePath\docs\developer_guide.md" -ErrorAction SilentlyContinue
Copy-Item "docs\client_vm_setup_checklist.md" "$ReleasePath\docs\client_vm_setup_checklist.md" -ErrorAction SilentlyContinue
Copy-Item "docs\sqlite_see_setup.md" "$ReleasePath\docs\sqlite_see_setup.md" -ErrorAction SilentlyContinue
Copy-Item "docs\keepass_setup.md" "$ReleasePath\docs\keepass_setup.md" -ErrorAction SilentlyContinue
Copy-Item "docs\solution_finalisation.md" "$ReleasePath\docs\solution_finalisation.md" -ErrorAction SilentlyContinue

Copy-Item "scripts\setup_client_vm_folders.ps1" "$ReleasePath\scripts\setup_client_vm_folders.ps1"
Copy-Item "scripts\create_windows_task_example.ps1" "$ReleasePath\scripts\create_windows_task_example.ps1"
Copy-Item "scripts\get_keepass_secret.ps1" "$ReleasePath\scripts\get_keepass_secret.ps1"
Copy-Item "scripts\README_keepass_setup.md" "$ReleasePath\scripts\README_keepass_setup.md"
Copy-Item "tools\sqlite-see\README.md" "$ReleasePath\tools\sqlite-see\README.md" -ErrorAction SilentlyContinue
Copy-Item "java\lib\README.md" "$ReleasePath\java\lib\README.md"
Copy-Item "java\lotus-corba-reader\README.md" "$ReleasePath\java\lotus-corba-reader\README.md"
Copy-Item "java\lotus-corba-reader\build.gradle" "$ReleasePath\java\lotus-corba-reader\build.gradle"
Copy-Item "java\lotus-corba-reader\settings.gradle" "$ReleasePath\java\lotus-corba-reader\settings.gradle"
Copy-Item "java\lotus-corba-reader\src" "$ReleasePath\java\lotus-corba-reader\src" -Recurse

$CorbaJar = "java\lotus-corba-reader\build\libs\lotus-corba-reader.jar"
if (Test-Path $CorbaJar) {
    Copy-Item $CorbaJar "$ReleasePath\java\lotus-corba-reader\lotus-corba-reader.jar"
}

@"
Internal Audit Data Extraction Release Bundle

Next steps on client VM:
1. Copy config\config.production.template.yaml to config\config.yaml.
2. Keep secrets.provider: keepass for production.
3. Create/populate the KeePass database entries for ORION_DB_PROD, FLEXCUBE_DB_PROD, HRIS_DB_PROD, and INTERNAL_AUDIT_DB_KEY.
4. Place the client-created .kdbx and .keyx files under secrets\ or update config.yaml to their approved paths.
5. Keep database.encryption: see for production.
6. Configure INTERNAL_AUDIT_DB_KEY in KeePass. It can be stored as the entry password or as custom field key.
7. Compile/copy the licensed SEE-enabled sqlite3.dll beside data-extraction.exe before running an encrypted DB.
8. Update config\config.yaml with KeePass entry titles and Lotus Excel file paths.
9. Keep Lotus Notes mode set to excel and place the extracts under lotus_notes\incoming.
   Phase 2 CORBA is optional. To enable it after VM validation, supply Java 8,
   notes.jar, ncso.jar, diiop_ior.txt, LOTUS_NOTES_PROD, and update config.yaml.
10. Run:
   .\data-extraction.exe --config .\config\config.yaml preflight
11. Verify packaged runtime dependencies for Oracle thin mode:
   .\data-extraction.exe --config .\config\config.yaml diagnose-runtime
   This must import cryptography, cffi, and oracledb successfully. If python-oracledb thin mode reports that cryptography cannot be imported, rebuild with the current PyInstaller spec and recreate this release bundle.
12. Test secrets:
   .\data-extraction.exe --config .\config\config.yaml test-secret ORION_DB_PROD 
   .\data-extraction.exe --config .\config\config.yaml test-secret FLEXCUBE_DB_PROD 
   .\data-extraction.exe --config .\config\config.yaml test-secret HRIS_DB_PROD 
   .\data-extraction.exe --config .\config\config.yaml test-secret INTERNAL_AUDIT_DB_KEY
13. Test all Oracle source connections:
   .\data-extraction.exe --config .\config\config.yaml test-source all
14. Run initial backfill:
   .\data-extraction.exe --config .\config\config.yaml run-backfill
15. Schedule daily run:
   .\data-extraction.exe --config .\config\config.yaml run-daily

SEE binaries, SEE source code, activation keys, database keys, KeePass databases, master passwords, key files, notes.jar, ncso.jar, diiop_ior.txt, passwords, and real Lotus exports are not included in this release bundle. Java CORBA is an optional Phase 2 mode; Excel remains the default fallback. The scripts\get_keepass_secret.ps1 wrapper remains available only as keepass_cli fallback. See docs\solution_finalisation.md, docs\sqlite_see_setup.md, and docs\keepass_setup.md.
"@ | Out-File "$ReleasePath\README_RELEASE.txt" -Encoding utf8

Write-Host ""
Write-Host "Release bundle created successfully."
Write-Host "Location: $ReleasePath"
Write-Host ""
Write-Host "Contents:"
Get-ChildItem $ReleasePath -Recurse | Select-Object FullName

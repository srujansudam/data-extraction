param(
    [string]$BasePath = "C:\InternalAuditDataExtraction"
)

Write-Host "Setting up Internal Audit Data Extraction folders..."
Write-Host "Base path: $BasePath"

$folders = @(
    $BasePath,
    "$BasePath\config",
    "$BasePath\data",
    "$BasePath\logs",
    "$BasePath\lotus_notes",
    "$BasePath\lotus_notes\incoming",
    "$BasePath\java",
    "$BasePath\java\lotus-corba-reader"
)

foreach ($folder in $folders) {
    if (-not (Test-Path $folder)) {
        New-Item -Path $folder -ItemType Directory | Out-Null
        Write-Host "Created: $folder"
    }
    else {
        Write-Host "Exists:  $folder"
    }
}

Write-Host ""
Write-Host "Folder setup complete."
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Copy data-extraction.exe to: $BasePath"
Write-Host "2. Copy config.yaml to: $BasePath\config\config.yaml"
Write-Host "3. Place Lotus Notes Excel extracts in: $BasePath\lotus_notes\incoming"
Write-Host "4. Run: $BasePath\data-extraction.exe preflight --config $BasePath\config\config.yaml"
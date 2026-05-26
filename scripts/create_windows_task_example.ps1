param(
    [string]$BasePath = "C:\InternalAuditDataExtraction",
    [string]$TaskName = "Internal Audit Data Extraction - Daily",
    [string]$RunTime = "02:00"
)

$ExePath = "$BasePath\data-extraction.exe"
$ConfigPath = "$BasePath\config\config.yaml"
$Arguments = "run-daily --config `"$ConfigPath`""

Write-Host "Creating Windows Scheduled Task example..."
Write-Host "Task name: $TaskName"
Write-Host "Executable: $ExePath"
Write-Host "Arguments: $Arguments"
Write-Host "Run time: $RunTime"

if (-not (Test-Path $ExePath)) {
    Write-Warning "Executable not found at $ExePath. Copy it before enabling the task."
}

if (-not (Test-Path $ConfigPath)) {
    Write-Warning "Config file not found at $ConfigPath. Create it before enabling the task."
}

$Action = New-ScheduledTaskAction `
    -Execute $ExePath `
    -Argument $Arguments `
    -WorkingDirectory $BasePath

$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At $RunTime

Write-Host ""
Write-Host "This script registers the task for the current user."
Write-Host "Client IT should review and configure the correct service account if required."
Write-Host ""

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Description "Runs the Internal Audit Data Extraction daily pipeline." `
    -Force

Write-Host "Scheduled task created or updated."
Write-Host ""
Write-Host "To inspect it:"
Write-Host "Task Scheduler > Task Scheduler Library > $TaskName"
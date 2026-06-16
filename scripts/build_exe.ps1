# Build the packaged Windows executable for data-extraction.
#
# This script is intended for local/release builds, not for storing client
# configuration or secrets. Keep real config files, SQLite database files,
# and logs outside the packaged executable.
#
# Output:
#   dist/data-extraction.exe
#
# The executable expects runtime folders/files such as config/config.yaml,
# data/, logs/, and Lotus input files to be copied beside it for deployment.

$ErrorActionPreference = "Stop"

Write-Host "Running pytest..."
pytest

Write-Host "Running Ruff..."
ruff check .

Write-Host "Removing previous build outputs..."
if (Test-Path "build") {
  Remove-Item "build" -Recurse -Force
}
if (Test-Path "dist") {
  Remove-Item "dist" -Recurse -Force
}

Write-Host "Building executable with PyInstaller..."
pyinstaller --clean data-extraction.spec

Write-Host "Build complete: dist/data-extraction.exe"

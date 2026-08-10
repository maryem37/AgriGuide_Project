# Start local backend (DB + all agents). From repo root:
#   .\dev.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  Write-Host "Shared venv missing - running setup first..."
  & ".\scripts\setup_venv.ps1"
}

docker compose up -d db
& ".\.venv\Scripts\python.exe" ".\scripts\run_backend.py"

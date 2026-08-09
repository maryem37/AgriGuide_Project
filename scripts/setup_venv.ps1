# One-time setup of the shared project virtualenv (Windows PowerShell).
# Usage (from repo root):
#   .\scripts\setup_venv.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".venv")) {
  Write-Host "Creating .venv ..."
  python -m venv .venv
}

$pip = ".\.venv\Scripts\python.exe"
& $pip -m pip install --upgrade pip
& $pip -m pip install -r requirements.txt

Write-Host ""
Write-Host "Optional Agriculture ML stack (chromadb/torch) - install with:"
Write-Host "  .\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt"
Write-Host ""
Write-Host "Then start everything with:"
Write-Host "  .\dev.ps1"

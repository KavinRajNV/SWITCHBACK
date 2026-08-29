# Switchback — start backend + frontend for local development.
# Usage:  pwsh scripts/dev.ps1        (from the repo root)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host '== Switchback dev bootstrap ==' -ForegroundColor Cyan

# 1. uv (Python project manager) --------------------------------------------
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not installed. Install it: https://docs.astral.sh/uv/getting-started/installation/"
}

# 2. .env ------------------------------------------------------------------
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host 'Created .env from .env.example. Fill in keys, or leave MONGODB_URI blank to use the local snapshot (docker compose up -d).' -ForegroundColor Yellow
}

# 3. backend venv + deps --------------------------------------------------
if (-not (Test-Path backend/.venv)) {
    Write-Host 'Creating backend/.venv (Python 3.11)...' -ForegroundColor Cyan
    uv venv backend/.venv --python 3.11
}
Write-Host 'Installing backend dependencies...' -ForegroundColor Cyan
uv pip install --python backend/.venv -r backend/requirements.txt | Out-Null

# 4. frontend deps ------------------------------------------------------
if (-not (Test-Path frontend/node_modules)) {
    Write-Host 'Installing frontend dependencies...' -ForegroundColor Cyan
    npm --prefix frontend install
}
if (-not (Test-Path frontend/.env)) { Copy-Item frontend/.env.example frontend/.env }

# 5. run both ---------------------------------------------------------
$backendCmd = "Set-Location '$root'; backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011 --reload"
Write-Host 'Starting backend on http://127.0.0.1:8011 (new window)...' -ForegroundColor Green
Start-Process pwsh -ArgumentList '-NoExit', '-Command', $backendCmd

Write-Host 'Starting frontend on http://127.0.0.1:5173 ...' -ForegroundColor Green
npm --prefix frontend run dev

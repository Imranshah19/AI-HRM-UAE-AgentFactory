#Requires -Version 5.1
<#
.SYNOPSIS
    AI-HRMS — Run WITHOUT Docker on Windows
.DESCRIPTION
    Starts the full stack natively:
      • PostgreSQL  (must be installed locally or via Chocolatey)
      • Redis       (must be installed locally or via Chocolatey / Memurai)
      • FastAPI     (uvicorn in a background window)
      • Next.js     (npm run dev in a background window)

    Prerequisites (install once):
      choco install postgresql15 redis-64 python311 nodejs-lts -y

    Or install manually:
      Python 3.11 : https://www.python.org/downloads/
      Node 20     : https://nodejs.org/
      PostgreSQL  : https://www.postgresql.org/download/windows/
      Redis       : https://github.com/tporadowski/redis/releases
                    (or Memurai: https://www.memurai.com/)

.EXAMPLE
    .\start_without_docker.ps1
    .\start_without_docker.ps1 -SkipBrowser
    .\start_without_docker.ps1 -Stop
#>
param(
    [switch]$Stop,
    [switch]$SkipBrowser,
    [string]$PgUser     = "hrms_user",
    [string]$PgPassword = "hrms_password",
    [string]$PgDb       = "hrms_db",
    [string]$PgPort     = "5432"
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step { param($msg) Write-Host "`n[STEP] $msg" -ForegroundColor Cyan }
function Write-Ok   { param($msg) Write-Host "[OK]   $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err  { param($msg) Write-Host "[ERR]  $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Gray }

# ── STOP mode ────────────────────────────────────────────────────────────────
if ($Stop) {
    Write-Host "Stopping AI-HRMS processes..." -ForegroundColor Yellow
    Get-Process -Name "uvicorn"  -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process -Name "node"     -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Ok "Stopped uvicorn and node processes."
    exit 0
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "  AI-HRMS — No-Docker Windows Starter" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta

# ── 1. Check prerequisites ────────────────────────────────────────────────────
Write-Step "Checking prerequisites..."

$missing = @()

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    $missing += "Python 3.11  → https://www.python.org/downloads/"
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    $missing += "Node.js 20   → https://nodejs.org/"
}
if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
    $missing += "PostgreSQL   → https://www.postgresql.org/download/windows/"
}
if (-not (Get-Command redis-cli -ErrorAction SilentlyContinue) -and
    -not (Get-Command redis-server -ErrorAction SilentlyContinue)) {
    $missing += "Redis        → https://github.com/tporadowski/redis/releases (or Memurai)"
}

if ($missing.Count -gt 0) {
    Write-Err "Missing prerequisites:"
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Quick install with Chocolatey (run as Administrator):" -ForegroundColor Yellow
    Write-Host '  choco install postgresql15 redis-64 python311 nodejs-lts -y' -ForegroundColor White
    Read-Host "`nPress Enter to exit"
    exit 1
}

Write-Ok "All prerequisites found."

# ── 2. Start PostgreSQL ───────────────────────────────────────────────────────
Write-Step "Ensuring PostgreSQL is running..."

# Try pg_ctl / net start / service
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pgService) {
    if ($pgService.Status -ne "Running") {
        Write-Info "Starting PostgreSQL service: $($pgService.Name)..."
        Start-Service $pgService.Name -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
    }
    Write-Ok "PostgreSQL service: $($pgService.Name) is running."
} else {
    Write-Warn "No PostgreSQL Windows service found. Assuming it is already running on port $PgPort."
}

# Create DB / user if not existing
Write-Info "Ensuring database '$PgDb' and user '$PgUser' exist..."
$env:PGPASSWORD = "postgres"

$createUser = @"
DO `$`$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$PgUser') THEN
    CREATE ROLE $PgUser LOGIN PASSWORD '$PgPassword';
  END IF;
END
`$`$;
"@

$createDb = "SELECT 'CREATE DATABASE $PgDb OWNER $PgUser' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$PgDb')\gexec"

psql -U postgres -p $PgPort -c $createUser 2>&1 | ForEach-Object { Write-Info $_ }
psql -U postgres -p $PgPort -c $createDb   2>&1 | ForEach-Object { Write-Info $_ }

Write-Ok "Database ready."

# ── 3. Start Redis ────────────────────────────────────────────────────────────
Write-Step "Ensuring Redis is running..."

$redisService = Get-Service -Name "redis*","memurai*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($redisService) {
    if ($redisService.Status -ne "Running") {
        Write-Info "Starting Redis service: $($redisService.Name)..."
        Start-Service $redisService.Name -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    Write-Ok "Redis service running."
} else {
    # Try launching redis-server in background window
    $redisBin = Get-Command redis-server -ErrorAction SilentlyContinue
    if ($redisBin) {
        Write-Info "Starting redis-server in background..."
        Start-Process "cmd.exe" -ArgumentList "/c title Redis && redis-server" -WindowStyle Minimized
        Start-Sleep -Seconds 2
        Write-Ok "redis-server started in background window."
    } else {
        Write-Warn "Could not start Redis automatically. Please start it manually."
    }
}

# ── 4. Backend Python venv + deps ─────────────────────────────────────────────
Write-Step "Setting up Python virtual environment..."

$backendDir = Join-Path $ScriptDir "backend"
$venvDir    = Join-Path $backendDir ".venv"

Push-Location $backendDir

if (-not (Test-Path $venvDir)) {
    Write-Info "Creating virtual environment..."
    python -m venv .venv
}

$activate = Join-Path $venvDir "Scripts\Activate.ps1"
. $activate

Write-Info "Installing/updating Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) {
    Write-Err "pip install failed. Check requirements.txt."
} else {
    Write-Ok "Python deps installed."
}

# ── 5. Run Alembic migrations ─────────────────────────────────────────────────
Write-Step "Running database migrations..."

$env:DATABASE_URL      = "postgresql+asyncpg://${PgUser}:${PgPassword}@localhost:${PgPort}/${PgDb}"
$env:DATABASE_SYNC_URL = "postgresql://${PgUser}:${PgPassword}@localhost:${PgPort}/${PgDb}"
$env:REDIS_URL         = "redis://localhost:6379/0"
$env:CELERY_BROKER_URL = "redis://localhost:6379/1"
$env:CELERY_RESULT_BACKEND = "redis://localhost:6379/2"
$env:JWT_SECRET_KEY    = "dev_secret_change_in_production"
$env:APP_ENV           = "development"
$env:DEBUG             = "true"
$env:STORAGE_BACKEND   = "local"
$env:LOCAL_UPLOAD_DIR  = (Join-Path $ScriptDir "uploads")
$env:FIRST_SUPERADMIN_EMAIL    = "admin@hrms.local"
$env:FIRST_SUPERADMIN_PASSWORD = "Admin@1234!"
$env:FIRST_SUPERADMIN_FIRST_NAME = "System"
$env:FIRST_SUPERADMIN_LAST_NAME  = "Admin"
$env:FRONTEND_URL = "http://localhost:3000"
$env:BACKEND_URL  = "http://localhost:8000"
$env:CORS_ORIGINS = "http://localhost:3000"

alembic upgrade head 2>&1 | ForEach-Object { Write-Info $_ }
Write-Ok "Migrations done."

# ── 6. Start FastAPI backend ──────────────────────────────────────────────────
Write-Step "Starting FastAPI backend (uvicorn --reload)..."

# Build environment block for the new window
$envBlock = @"
set DATABASE_URL=postgresql+asyncpg://${PgUser}:${PgPassword}@localhost:${PgPort}/${PgDb}
set DATABASE_SYNC_URL=postgresql://${PgUser}:${PgPassword}@localhost:${PgPort}/${PgDb}
set REDIS_URL=redis://localhost:6379/0
set CELERY_BROKER_URL=redis://localhost:6379/1
set CELERY_RESULT_BACKEND=redis://localhost:6379/2
set JWT_SECRET_KEY=dev_secret_change_in_production
set APP_ENV=development
set DEBUG=true
set STORAGE_BACKEND=local
set LOCAL_UPLOAD_DIR=$(Join-Path $ScriptDir 'uploads')
set FIRST_SUPERADMIN_EMAIL=admin@hrms.local
set FIRST_SUPERADMIN_PASSWORD=Admin@1234!
set FIRST_SUPERADMIN_FIRST_NAME=System
set FIRST_SUPERADMIN_LAST_NAME=Admin
set FRONTEND_URL=http://localhost:3000
set BACKEND_URL=http://localhost:8000
set CORS_ORIGINS=http://localhost:3000
"@

$backendCmd = "cd /d `"$backendDir`" && call .venv\Scripts\activate.bat && $envBlock && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process "cmd.exe" -ArgumentList "/c title AI-HRMS Backend && $backendCmd" -WindowStyle Normal

Pop-Location
Write-Ok "FastAPI backend started in new window (port 8000)."

# ── 7. Frontend npm deps + dev server ─────────────────────────────────────────
Write-Step "Starting Next.js frontend..."

Push-Location $ScriptDir

if (-not (Test-Path "node_modules")) {
    Write-Info "Installing npm packages..."
    npm install
}

$frontendCmd = "cd /d `"$ScriptDir`" && set NEXT_PUBLIC_API_URL=http://localhost:8000 && set NEXT_PUBLIC_APP_NAME=AI-HRMS && npm run dev"
Start-Process "cmd.exe" -ArgumentList "/c title AI-HRMS Frontend && $frontendCmd" -WindowStyle Normal

Pop-Location
Write-Ok "Next.js frontend started in new window (port 3000)."

# ── 8. Wait and open browser ──────────────────────────────────────────────────
Write-Info "Waiting 10s for services to initialise..."
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  AI-HRMS is running WITHOUT Docker!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend  : http://localhost:3000" -ForegroundColor White
Write-Host "  Backend   : http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs  : http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "  Default login: admin@hrms.local / Admin@1234!" -ForegroundColor Yellow
Write-Host ""
Write-Host "  To stop:  .\start_without_docker.ps1 -Stop" -ForegroundColor Gray
Write-Host "            (or just close the Backend/Frontend windows)" -ForegroundColor Gray
Write-Host ""

if (-not $SkipBrowser) {
    Start-Process "http://localhost:3000"
}

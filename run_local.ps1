#Requires -Version 5.1
<#
.SYNOPSIS
    AI-HRMS Windows Local Runner (PowerShell)
.DESCRIPTION
    - Verifies Docker Desktop is running
    - Fixes Docker daemon DNS to 8.8.8.8 / 8.8.4.4
    - Pre-pulls base images
    - Stops old containers, builds and starts all services
    - Waits for health checks
    - Runs Alembic migrations
    - Opens browser at http://localhost:3000
.EXAMPLE
    .\run_local.ps1
    .\run_local.ps1 -SkipBrowser
    .\run_local.ps1 -NoBuild
#>
param(
    [switch]$SkipBrowser,
    [switch]$NoBuild,
    [switch]$Logs
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "AI-HRMS Local Runner"

function Write-Step  { param($msg) Write-Host "`n[STEP] $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "[OK]   $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err   { param($msg) Write-Host "[ERR]  $msg" -ForegroundColor Red }
function Write-Info  { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Gray }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "  AI-HRMS — Windows Local Runner (PowerShell)" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta

# ── 1. Check Docker ───────────────────────────────────────────────────────────
Write-Step "Checking Docker Desktop..."

$dockerRunning = $false
try {
    $null = docker info 2>&1
    $dockerRunning = $LASTEXITCODE -eq 0
} catch {}

if (-not $dockerRunning) {
    Write-Err "Docker Desktop is not running."
    Write-Info "Starting Docker Desktop..."

    $dockerExe = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerExe) {
        Start-Process $dockerExe
        Write-Info "Waiting for Docker to start (up to 60s)..."
        $waited = 0
        do {
            Start-Sleep -Seconds 5
            $waited += 5
            try { $null = docker info 2>&1; $dockerRunning = $LASTEXITCODE -eq 0 } catch {}
        } while (-not $dockerRunning -and $waited -lt 60)
    }

    if (-not $dockerRunning) {
        Write-Err "Docker did not start. Please launch Docker Desktop manually, then rerun this script."
        Read-Host "Press Enter to exit"
        exit 1
    }
}
Write-Ok "Docker is running."

# ── 2. Fix Docker daemon DNS ──────────────────────────────────────────────────
Write-Step "Checking Docker daemon DNS configuration..."

$daemonPath = "$env:APPDATA\Docker\daemon.json"
$restartRequired = $false

if (Test-Path $daemonPath) {
    $daemonJson = Get-Content $daemonPath -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
    if (-not $daemonJson) { $daemonJson = [PSCustomObject]@{} }
} else {
    $daemonJson = [PSCustomObject]@{}
}

$currentDns = $daemonJson.dns
$wantedDns  = @("8.8.8.8", "8.8.4.4")
$needsDns   = ($null -eq $currentDns) -or
              (-not ($currentDns -contains "8.8.8.8"))

if ($needsDns) {
    Write-Info "Adding DNS 8.8.8.8 / 8.8.4.4 to Docker daemon.json..."
    $daemonJson | Add-Member -NotePropertyName "dns" -NotePropertyValue $wantedDns -Force
    $daemonJson | ConvertTo-Json -Depth 10 | Set-Content $daemonPath -Encoding UTF8
    Write-Warn "Docker daemon.json updated. Docker Desktop should pick this up automatically."
    Write-Warn "If image pulls still fail: open Docker Desktop > Settings > Docker Engine, verify DNS, Apply & Restart."
    $restartRequired = $true
} else {
    Write-Ok "DNS already configured: $($currentDns -join ', ')"
}

# ── 3. Pre-pull base images ───────────────────────────────────────────────────
Write-Step "Pre-pulling base images..."

foreach ($img in @("python:3.11-slim", "node:20-alpine")) {
    Write-Info "Pulling $img ..."
    docker pull $img 2>&1 | ForEach-Object { Write-Info $_ }
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Could not pull $img. Will attempt during build."
        Write-Warn "If this fails repeatedly, open Docker Desktop > Settings > Docker Engine"
        Write-Warn "and add: `"dns`": [`"8.8.8.8`", `"8.8.4.4`"]  then Apply & Restart."
    } else {
        Write-Ok "$img pulled."
    }
}

# ── 4. Stop existing containers ───────────────────────────────────────────────
Write-Step "Stopping existing containers..."
docker-compose -f docker-compose.yml -f docker-compose.local.yml down --remove-orphans 2>&1 |
    ForEach-Object { Write-Info $_ }
Write-Ok "Stopped."

# ── 5. Build and start ────────────────────────────────────────────────────────
Write-Step "Building and starting all services..."

$upArgs = @("-f", "docker-compose.yml", "-f", "docker-compose.local.yml", "up", "-d")
if (-not $NoBuild) { $upArgs += "--build" }

docker-compose @upArgs
if ($LASTEXITCODE -ne 0) {
    Write-Err "docker-compose up failed. See output above."
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Open Docker Desktop > Settings > Docker Engine"
    Write-Host '     Add:  "dns": ["8.8.8.8", "8.8.4.4"]'
    Write-Host "     Click Apply & Restart"
    Write-Host "  2. docker pull python:3.11-slim"
    Write-Host "  3. docker pull node:20-alpine"
    Write-Host "  4. Rerun this script"
    Read-Host "`nPress Enter to exit"
    exit 1
}
Write-Ok "Services started."

# ── 6. Wait for backend health ────────────────────────────────────────────────
Write-Step "Waiting for backend health check..."

$maxWait = 90
$waited  = 0
$healthy = $false

while ($waited -lt $maxWait) {
    try {
        $resp = docker exec hrms_backend curl -sf http://localhost:8000/health 2>&1
        if ($LASTEXITCODE -eq 0) { $healthy = $true; break }
    } catch {}
    Write-Info "Backend not ready yet ($waited/$maxWait s)..."
    Start-Sleep -Seconds 5
    $waited += 5
}

if ($healthy) {
    Write-Ok "Backend is healthy."
} else {
    Write-Warn "Backend did not become healthy within ${maxWait}s."
    Write-Warn "Check logs: docker-compose logs backend"
}

# ── 7. Run migrations ─────────────────────────────────────────────────────────
Write-Step "Running database migrations..."
docker exec hrms_backend alembic upgrade head 2>&1 | ForEach-Object { Write-Info $_ }
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Migration returned non-zero — may already be up to date."
} else {
    Write-Ok "Migrations applied."
}

# ── 8. Summary ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  All services are running!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend  : http://localhost:3000" -ForegroundColor White
Write-Host "  Backend   : http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs  : http://localhost:8000/docs" -ForegroundColor White
Write-Host "  PostgreSQL: localhost:5432  (hrms_user / hrms_password)" -ForegroundColor White
Write-Host "  Redis     : localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "  Default login: admin@hrms.local / Admin@1234!" -ForegroundColor Yellow
Write-Host ""

# ── 9. Open browser ───────────────────────────────────────────────────────────
if (-not $SkipBrowser) {
    Write-Info "Opening browser at http://localhost:3000 ..."
    Start-Process "http://localhost:3000"
}

# ── 10. Show logs ─────────────────────────────────────────────────────────────
if ($Logs) {
    Write-Info "Tailing logs (Ctrl+C to stop watching, containers keep running)..."
    docker-compose -f docker-compose.yml -f docker-compose.local.yml logs -f --tail=50
}

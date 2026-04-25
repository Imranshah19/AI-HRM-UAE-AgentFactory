@echo off
setlocal enabledelayedexpansion
title AI-HRMS Local Runner

echo.
echo ============================================================
echo  AI-HRMS — Windows Local Runner
echo ============================================================
echo.

:: ── 1. Check Docker is running ───────────────────────────────
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)
echo [OK] Docker is running

:: ── 2. Fix Docker daemon DNS (writes to daemon.json) ─────────
echo [INFO] Checking Docker daemon DNS settings...
set "DAEMON_JSON=%APPDATA%\Docker\daemon.json"

if not exist "%DAEMON_JSON%" (
    echo [INFO] Creating Docker daemon.json with DNS 8.8.8.8 ...
    echo {"dns": ["8.8.8.8", "8.8.4.4"]} > "%DAEMON_JSON%"
    echo [WARN] Docker daemon.json was created. Docker Desktop may need to restart.
    echo [WARN] If images still fail, open Docker Desktop ^> Settings ^> Docker Engine
    echo [WARN] and confirm {"dns": ["8.8.8.8", "8.8.4.4"]} is present, then Apply ^& Restart.
    echo.
)

:: ── 3. Pre-pull Python and Node images with explicit DNS ──────
echo [INFO] Pre-pulling base images (with retry)...

docker pull python:3.11-slim
if errorlevel 1 (
    echo [WARN] Failed to pull python:3.11-slim — will try during build.
    echo [HINT] If this keeps failing, open Docker Desktop ^> Settings ^> Docker Engine
    echo [HINT] Add: "dns": ["8.8.8.8", "8.8.4.4"]  then Apply ^& Restart Docker.
)

docker pull node:20-alpine
if errorlevel 1 (
    echo [WARN] Failed to pull node:20-alpine — will try during build.
)

:: ── 4. Stop existing containers ───────────────────────────────
echo.
echo [INFO] Stopping existing containers...
docker-compose -f docker-compose.yml -f docker-compose.local.yml down --remove-orphans
echo [OK] Stopped.

:: ── 5. Build and start all services ──────────────────────────
echo.
echo [INFO] Building and starting all services...
docker-compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
if errorlevel 1 (
    echo.
    echo [ERROR] docker-compose failed. See errors above.
    echo.
    echo Troubleshooting tips:
    echo  1. Open Docker Desktop ^> Settings ^> Docker Engine
    echo     Add: "dns": ["8.8.8.8", "8.8.4.4"]
    echo     Click Apply ^& Restart
    echo  2. Run: docker pull python:3.11-slim
    echo  3. Run: docker pull node:20-alpine
    echo  4. Then retry: run_local.bat
    pause
    exit /b 1
)

echo.
echo [OK] All services started.

:: ── 6. Wait for backend to be healthy ────────────────────────
echo.
echo [INFO] Waiting for backend to be ready (up to 60s)...
set /a tries=0
:wait_loop
set /a tries+=1
if %tries% gtr 12 (
    echo [WARN] Backend not healthy yet — check logs: docker-compose logs backend
    goto show_logs
)
docker exec hrms_backend curl -sf http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo [INFO] Waiting... (%tries%/12)
    timeout /t 5 /nobreak >nul
    goto wait_loop
)
echo [OK] Backend is healthy.

:: ── 7. Run migrations ─────────────────────────────────────────
echo.
echo [INFO] Running database migrations...
docker exec hrms_backend alembic upgrade head
if errorlevel 1 (
    echo [WARN] Migration failed — it may already be up to date.
)

:show_logs
:: ── 8. Summary ───────────────────────────────────────────────
echo.
echo ============================================================
echo  Services running:
echo    Frontend  : http://localhost:3000
echo    Backend   : http://localhost:8000
echo    API Docs  : http://localhost:8000/docs
echo    PostgreSQL: localhost:5432  (hrms_user / hrms_password)
echo    Redis     : localhost:6379
echo.
echo  Default login: admin@hrms.local / Admin@1234!
echo ============================================================
echo.
echo [INFO] Tailing logs (Ctrl+C to stop watching, containers keep running)...
echo.
docker-compose -f docker-compose.yml -f docker-compose.local.yml logs -f --tail=50

endlocal

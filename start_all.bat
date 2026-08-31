@echo off
TITLE CityTrack AI - Multi-Service Launcher
COLOR 0A

echo ===============================================================================
echo                CITYTRACK AI - SYSTEM LAUNCHER (PS 26127)
echo ===============================================================================
echo.

cd /d "%~dp0"

:: 1. Check Docker & Start Containers if available
echo [1/4] Checking Database ^& Redis containers...
docker info >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [INFO] Docker is running. Launching PostGIS DB and Redis...
    docker compose up db redis -d
    echo [INFO] Waiting for database readiness (5s)...
    timeout /t 5 /nobreak >nul
) else (
    echo [WARN] Docker is not running or not installed.
    echo        The application will run with live in-memory fallbacks.
    echo        (To enable persistent PostGIS, start Docker Desktop and re-run this script)
)
echo.

:: 2. Check Python Virtual Environment & DB migrations
echo [2/4] Initializing Python Virtual Environment...
if exist ".venv\Scripts\python.exe" (
    echo [INFO] Python virtual environment found.
    
    :: Run Alembic migrations and Seeding if DB is reachable
    docker info >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo [INFO] Running database migrations...
        call .venv\Scripts\alembic.exe upgrade head >nul 2>&1
        echo [INFO] Seeding Pan-India 6-metro surveillance network...
        call .venv\Scripts\python.exe tools\seed_pan_india.py >nul 2>&1
    )
) else (
    echo [ERROR] Virtual environment not found at .venv\Scripts\python.exe!
    echo         Please setup venv first: python -m venv .venv ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)
echo.

:: 3. Launch Backend API in a separate terminal window
echo [3/4] Launching FastAPI Backend on http://localhost:8000 ...
start "CityTrack AI - Backend API (FastAPI)" cmd /k "cd /d %~dp0 && title CityTrack AI - Backend && color 0B && .venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Brief pause to give backend time to bind port
timeout /t 2 /nobreak >nul

:: 4. Launch Frontend Dev Server in a separate terminal window
echo [4/4] Launching React 19 Frontend on http://localhost:3000 ...
start "CityTrack AI - Command Center UI (Vite)" cmd /k "cd /d %~dp0frontend && title CityTrack AI - Frontend && color 0E && npm run dev"

:: Open default browser
timeout /t 3 /nobreak >nul
echo.
echo ===============================================================================
echo                ALL SERVICES LAUNCHED SUCCESSFULLY!
echo ===============================================================================
echo  - Command Center UI:  http://localhost:3000
echo  - Backend API Docs:   http://localhost:8000/docs
echo  - API Health Probe:   http://localhost:8000/api/v1/health
echo  - Live SSE Stream:    http://localhost:8000/api/v1/events/stream
echo ===============================================================================
echo Opening browser...
start http://localhost:3000

echo.
echo Press any key to exit this launcher window (services will stay running).
pause >nul

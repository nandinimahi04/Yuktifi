@echo off
setlocal enabledelayedexpansion
REM ─────────────────────────────────────────────────────────────────────────────
REM YUKTI launcher.
REM
REM This used to require a pre-made backend\.venv and printed "create it first"
REM and exited. For anyone evaluating the project, that is the first thing they
REM hit, so it now builds the environment itself.
REM ─────────────────────────────────────────────────────────────────────────────
cd /d "%~dp0"

if not exist "backend\app\main.py" (
  echo [x] backend\app\main.py not found - is this the right directory?
  exit /b 1
)

REM ── Backend environment ──────────────────────────────────────────────────────
if exist "backend\.venv\Scripts\python.exe" (
  echo [ok] backend virtualenv present
) else (
  echo [--] creating backend virtualenv...
  where py >nul 2>&1
  if !errorlevel!==0 (
    py -3 -m venv backend\.venv
  ) else (
    python -m venv backend\.venv
  )
  if errorlevel 1 (
    echo [x] could not create the virtualenv. Install Python 3.11+ and retry.
    exit /b 1
  )
  echo [--] installing backend requirements - this takes a minute...
  "backend\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
  "backend\.venv\Scripts\python.exe" -m pip install -r backend\requirements.txt --quiet
  if errorlevel 1 (
    echo [x] dependency install failed. See the output above.
    exit /b 1
  )
  echo [ok] backend environment ready
)

REM ── Configuration ────────────────────────────────────────────────────────────
if not exist "backend\.env" (
  if exist "backend\.env.example" (
    copy /y "backend\.env.example" "backend\.env" >nul
    echo [ok] created backend\.env from .env.example
    echo     Data providers will be unavailable until keys are added.
    echo     The app runs and discloses the gaps; it does not fabricate them.
  )
)

REM ── Database ─────────────────────────────────────────────────────────────────
REM Tables are created on startup by init_db(), so no seed step is required and
REM no database file is shipped. See docs\FINANCIAL_MODEL.md.
if exist "backend\yukti.db" (
  echo [--] backend\yukti.db exists and will be reused.
  echo     Delete it for a clean run.
)

REM ── Start ────────────────────────────────────────────────────────────────────
REM start /D sets the working directory, which avoids nesting escaped quotes
REM inside cmd /k - the previous form was fragile enough to break on paths with
REM spaces.
start "YUKTI Backend" /D "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
echo [ok] backend starting on http://localhost:8000  ^(docs at /docs^)

if exist "frontend\package.json" (
  where node >nul 2>&1
  if errorlevel 1 (
    echo [--] node not found - skipping the frontend. Backend only.
  ) else (
    if not exist "frontend\node_modules" (
      echo [--] installing frontend dependencies...
      pushd "%~dp0frontend"
      call npm install --silent
      popd
    )
    start "YUKTI Frontend" /D "%~dp0frontend" cmd /k "npm run dev"
    echo [ok] frontend starting on http://localhost:3000
  )
) else (
  echo [--] frontend\package.json not found - backend only.
)

echo.
echo Both windows stay open. Close them to stop.
echo Verify the model:  cd backend ^&^& .venv\Scripts\python.exe -m pytest tests -q
endlocal

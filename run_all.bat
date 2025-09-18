@echo off
setlocal enabledelayedexpansion

REM =========================
REM  SeedAI — run_all.bat (hardened v2)
REM  Kills stale procs, rotates logs, waits for Ollama via curl,
REM  starts: Ollama + Backend + Frontend, runs reporter once.
REM =========================

REM ---- CONFIG (edit as needed) ----
REM If you want to force a specific Python, set full path:
REM set "PYTHON_EXE=D:\Conda3.11.9\CondaOfflineBundle2\_work\mc\python.exe"
set "PYTHON_EXE=python"

set "BACKEND_HOST=0.0.0.0"
set "BACKEND_PORT=8090"
set "FRONTEND_DIR=openweb-ui-frontend"

set "OLLAMA_BASE_URL=http://127.0.0.1:11434"
set "OLLAMA_API_KEY=ollama"
set "AURELIA_DEFAULT_MODEL=llama3.2-vision:11b"

REM ---- Prep ----
set "ROOT=%~dp0"
cd /d "%ROOT%"
if not exist logs mkdir logs

REM ---- Timestamp (YYYYMMDD-HHMMSS) ----
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set "Y=%%c" & set "M=%%a" & set "D=%%b"
for /f "tokens=1-4 delims=:." %%h in ("%time%") do set "HH=%%h" & set "MM=%%i" & set "SS=%%j"
set "HH=0%HH%" & set "HH=%HH:~-2%"
set "TS=%Y%%M%%D%-%HH%%MM%%SS%"

set "LOG_OLLAMA=logs\ollama-%TS%.log"
set "LOG_BACKEND=logs\backend-%TS%.log"
set "LOG_FRONTEND=logs\frontend-%TS%.log"
set "LOG_REPORTER=logs\reporter-%TS%.log"

REM ---- Show config ----
echo ===========================================
echo  SeedAI Launcher
echo  OLLAMA_BASE_URL   = %OLLAMA_BASE_URL%
echo  DEFAULT_MODEL     = %AURELIA_DEFAULT_MODEL%
echo  BACKEND           = %BACKEND_HOST%:%BACKEND_PORT%
echo  PYTHON_EXE        = %PYTHON_EXE%
echo  FRONTEND_DIR      = %FRONTEND_DIR%
echo  Logs folder       = %ROOT%logs
echo  Timestamp         = %TS%
echo ===========================================
echo.

REM ==========================================================
REM Stop any previous runs so logs aren't locked / ports busy
REM ==========================================================
echo [Stop] killing stale windows (ollama/backend/frontend)...
for %%T in ("ollama" "backend" "frontend") do (
  taskkill /FI "WINDOWTITLE eq %%~T" /F /T >NUL 2>&1
)
echo [Stop] killing common processes (best effort)...
for %%P in (uvicorn.exe python.exe node.exe ollama.exe) do (
  taskkill /IM %%P /F /T >NUL 2>&1
)

REM Small pause to free files
ping 127.0.0.1 -n 2 >NUL

REM Clear any old “latest” symlinks
del /f /q logs\backend.log logs\frontend.log logs\ollama.log logs\reporter.log 2>NUL

REM ---- Export env for children ----
set "PYTHONPATH=."
set "PYTHONNOUSERSITE=1"
set "OLLAMA_BASE_URL=%OLLAMA_BASE_URL%"
set "OLLAMA_API_KEY=%OLLAMA_API_KEY%"
set "AURELIA_DEFAULT_MODEL=%AURELIA_DEFAULT_MODEL%"
set "AURELIA_PERSONA_PATH=seedai\persona_aurelia.md"
set "AURELIA_BOOTSTRAP_MAX=4000"
set "DEV_AUTH=true"
set "GATEWAY_API_KEY=ollama"

REM ---- Start Ollama (ignore AutoRun with /d) ----
echo [Ollama] starting -> %LOG_OLLAMA%
start "ollama" /min cmd /d /c "ollama serve >> "%LOG_OLLAMA%" 2>&1"

REM ---- Wait for Ollama readiness (curl loop, up to 30s) ----
echo [Ollama] waiting to become ready...
set /a _tries=0
:OLLAMA_WAIT
set /a _tries+=1
curl -s --max-time 2 "%OLLAMA_BASE_URL%/v1/models" >NUL 2>&1
if %errorlevel%==0 (
  echo [OK] Ollama is responding.
) else (
  if %_tries% GEQ 30 (
    echo [WARN] Ollama did not respond after 30s. Continuing anyway...
  ) else (
    timeout /t 1 >NUL
    goto :OLLAMA_WAIT
  )
)

REM ---- Verify Python ----
echo [Python] checking interpreter...
"%PYTHON_EXE%" --version 1>> "%LOG_BACKEND%" 2>&1
if errorlevel 9009 (
  echo [ERROR] PYTHON_EXE not found: %PYTHON_EXE%
  echo         Edit run_all.bat and set PYTHON_EXE to a valid python.exe
  goto :end
)

REM ---- Start Backend (Uvicorn) ----
echo [Backend] starting uvicorn -> %LOG_BACKEND%
start "backend" /min cmd /d /c "%PYTHON_EXE% -m uvicorn gateway.app:app --host %BACKEND_HOST% --port %BACKEND_PORT% --log-level info >> "%LOG_BACKEND%" 2>&1"

REM ---- Start Frontend (Vite/OpenWebUI) ----
if not exist "%FRONTEND_DIR%\package.json" (
  echo [Frontend] %FRONTEND_DIR%\package.json not found. Skipping frontend start.
) else (
  echo [Frontend] starting dev server -> %LOG_FRONTEND%
  pushd "%FRONTEND_DIR%"
  start "frontend" /min cmd /d /c "npm run dev >> "..\%LOG_FRONTEND%" 2>&1"
  popd
)

REM ---- Run Reporter once (non-blocking) ----
echo [Reporter] running progress reporter -> %LOG_REPORTER%
"%PYTHON_EXE%" -m tools.progress_report >> "%LOG_REPORTER%" 2>&1

REM ---- Point 'latest' aliases to newest logs (copy) ----
copy /y "%LOG_OLLAMA%"   logs\ollama.log   >NUL
copy /y "%LOG_BACKEND%"  logs\backend.log  >NUL
copy /y "%LOG_FRONTEND%" logs\frontend.log >NUL
copy /y "%LOG_REPORTER%" logs\reporter.log >NUL

echo.
echo ✅ All services launched.
echo  - Frontend: http://127.0.0.1:5173
echo  - Backend : http://127.0.0.1:%BACKEND_PORT%
echo  - Models  : %OLLAMA_BASE_URL%/v1/models
echo  Logs:
echo    - %LOG_OLLAMA%
echo    - %LOG_BACKEND%
echo    - %LOG_FRONTEND%
echo    - %LOG_REPORTER%
echo.
pause
:end

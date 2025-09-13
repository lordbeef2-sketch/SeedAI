@echo off
echo Starting SeedAI System...
echo.

echo Starting SeedAI API Server...
start "SeedAI API" cmd /c "run_seedai_api.bat"

timeout /t 2 /nobreak > nul

echo Starting OpenWebUI Backend Server...
start "Backend Server" cmd /c "run_backend.bat"

timeout /t 3 /nobreak > nul

echo Starting Frontend Dev Server...
start "Frontend Dev Server" cmd /c "run_frontend.bat"

echo.
echo All servers are starting up!
echo SeedAI API: http://localhost:8000
echo OpenWebUI Backend: http://localhost:8080
echo Frontend: http://localhost:5173 (will open automatically)
echo.
pause
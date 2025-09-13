@echo off
echo Starting Complete SeedAI Ecosystem...
echo.

echo Starting SeedAI API Server...
start "SeedAI API" cmd /c "run_seedai_api.bat"

timeout /t 2 /nobreak > nul

echo Starting OpenWebUI Backend Server...
start "Backend Server" cmd /c "run_backend.bat"

timeout /t 3 /nobreak > nul

echo Starting Frontend Dev Server...
start "Frontend Dev Server" cmd /c "run_frontend.bat"

timeout /t 2 /nobreak > nul

echo Starting SeedAI Tkinter GUI...
start "SeedAI GUI" cmd /c "python gui.py"

echo.
echo All components are starting up!
echo ===========================================
echo SeedAI API: http://localhost:8000
echo OpenWebUI Backend: http://localhost:8080
echo Frontend: http://localhost:5173
echo SeedAI GUI: Tkinter window (should open)
echo ===========================================
echo.
echo Model selection should now work in the web interface!
echo.
pause
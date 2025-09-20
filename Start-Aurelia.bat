@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Aurelia.ps1" -OpenBrowser -BackendNewWindow -FrontendNewWindow
endlocal
exit /b 0

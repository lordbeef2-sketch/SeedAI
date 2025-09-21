@echo off
git status
timeout /t 10 /nobreak >nul
git add .
timeout /t 15 /nobreak >nul
git commit -m "Update project files"
timeout /t 10 /nobreak >nul
git push origin main
@echo off
git status
wait -n
git add .
wait -n
git commit -m "Update project files"
wait -n
git push origin main
wait -n
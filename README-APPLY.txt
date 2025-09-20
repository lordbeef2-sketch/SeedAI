SeedAI — Aurelia Patch 002
==========================

This zip contains:
  - Start-Aurelia.ps1 / Start-Aurelia.bat  : one-click starter (backend 8090 + frontend 5173)
  - openweb-ui-frontend/.env.development   : VITE_API_URL -> http://localhost:8090/api
  - gateway/openwebui_models_probe.py      : resilient /api/models for Ollama
  - gateway/diagnostics.py                 : /diag/health and /diag/memory/test-write
  - tools/Apply-Patch.ps1                  : safely injects router includes into gateway/app.py

Apply steps (from repo root, e.g., D:\SeedAI):

  1) Unzip, preserving paths. You should now have:
     D:\SeedAI\Start-Aurelia.ps1
     D:\SeedAI\Start-Aurelia.bat
     D:\SeedAI\openweb-ui-frontend\.env.development
     D:\SeedAI\gateway\openwebui_models_probe.py
     D:\SeedAI\gateway\diagnostics.py
     D:\SeedAI\tools\Apply-Patch.ps1

  2) Patch your app.py to include the routers:
     powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Apply-Patch.ps1
     # Add -ServeStatic if you want the backend to serve the built GUI at / :
     # powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Apply-Patch.ps1 -ServeStatic

  3) Ensure Ollama has a model:
     ollama list
     ollama pull llama3.2-vision:11b

  4) Start with one click:
     Start-Aurelia.bat      (or)
     powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Aurelia.ps1 -OpenBrowser -BackendNewWindow -FrontendNewWindow

  5) Sanity checks:
     http://localhost:8090/diag/health
     http://localhost:8090/api/models
     http://localhost:5173

     To verify persistence:
     Invoke-RestMethod -Method POST -Uri http://localhost:8090/diag/memory/test-write `
       -Body (@{ note = "first run" } | ConvertTo-Json) -ContentType "application/json"

     Get-Content .\memory\core.json -Raw

If anything doesn't apply cleanly, you can copy the files into place by hand and use the Apply-Patch.ps1
script to adjust gateway/app.py, or I can tailor a repo-specific patch for your exact file contents.

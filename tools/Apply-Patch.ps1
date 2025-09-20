param(
  [switch]$ServeStatic  # also mount built GUI from openweb-ui-frontend/dist
)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Path $PSCommandPath -Parent
$AppPath  = Join-Path $RepoRoot "..\gateway\app.py" | Resolve-Path
$AppText  = Get-Content $AppPath -Raw

# Backup
Copy-Item $AppPath "$AppPath.bak" -Force

# Ensure imports
if ($AppText -notmatch "from fastapi import FastAPI") {
  Write-Warning "Could not find 'from fastapi import FastAPI' in app.py; script will continue."
}
if ($AppText -notmatch "openwebui_models_probe") {
  $AppText = $AppText -replace "(from fastapi import FastAPI[^\r\n]*[\r\n])", "`$1from .openwebui_models_probe import router as models_probe`r`n"
}
if ($AppText -notmatch "diagnostics import router") {
  if ($AppText -match "from fastapi import FastAPI[^\r\n]*[\r\n]") {
    $AppText = $AppText -replace "(from fastapi import FastAPI[^\r\n]*[\r\n])", "`$1from .diagnostics import router as diag_router`r`n"
  } else {
    $AppText = "from .diagnostics import router as diag_router`r`n" + $AppText
  }
}

# Include routers after app = FastAPI(...)
if ($AppText -notmatch "include_router\(models_probe\)") {
  $AppText = $AppText -replace "(app\s*=\s*FastAPI\(.*?\)[\r\n])", "`$1app.include_router(models_probe)`r`n"
}
if ($AppText -notmatch "include_router\(diag_router\)") {
  $AppText = $AppText -replace "(app\s*=\s*FastAPI\(.*?\)[\r\n])", "`$1app.include_router(diag_router)`r`n"
}

# Optional: mount static GUI
if ($ServeStatic) {
  if ($AppText -notmatch "from fastapi.staticfiles import StaticFiles") {
    $AppText = $AppText -replace "(from fastapi import FastAPI[^\r\n]*[\r\n])", "`$1from fastapi.staticfiles import StaticFiles`r`n"
  }
  if ($AppText -notmatch "app\.mount\(\"/\", StaticFiles\(directory=.*?dist") {
    $mount = "app.mount(\"/\", StaticFiles(directory=\"openweb-ui-frontend/dist\", html=True), name=\"static\")"
    if ($AppText -match "(app\.include_router.*[\r\n])+"){
      $AppText = $AppText + "`r`n" + $mount + "`r`n"
    } else {
      $AppText = $AppText + "`r`n" + $mount + "`r`n"
    }
  }
}

Set-Content -Encoding UTF8 $AppPath $AppText
Write-Host "Patched $AppPath"

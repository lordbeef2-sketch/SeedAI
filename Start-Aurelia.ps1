<# Start-Aurelia.ps1 — mirrors run_all.bat
   - venv autodetect
   - sets CORS + VITE
   - waits for Ollama (/v1/models) and Backend (/docs)
   - syncs runtime endpoints into memory\core.json
#>

param(
  [string]$PythonExe = "python",
  [string]$BackendHost = "0.0.0.0",
  [int]$BackendPort = 8090,
  [string]$FrontendDir = "openweb-ui-frontend",
  [switch]$SkipOllama,
  [switch]$BackendNewWindow,
  [switch]$FrontendNewWindow,
  [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

# ---- Paths ----
$RepoRoot  = Split-Path -Path $PSCommandPath -Parent
Set-Location $RepoRoot
$LogsDir   = Join-Path $RepoRoot "logs"
$MemoryDir = Join-Path $RepoRoot "memory"
$CoreJson  = Join-Path $MemoryDir "core.json"

# Prefer repo venv if present
$venvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPy) { $PythonExe = $venvPy }

# Ensure dirs
if (-not (Test-Path $LogsDir))   { New-Item -ItemType Directory -Path $LogsDir   | Out-Null }
if (-not (Test-Path $MemoryDir)) { New-Item -ItemType Directory -Path $MemoryDir | Out-Null }

# ---- Env wiring ----
if (-not $env:OLLAMA_BASE_URL)       { $env:OLLAMA_BASE_URL       = "http://127.0.0.1:11434" }
if (-not $env:AURELIA_DEFAULT_MODEL) { $env:AURELIA_DEFAULT_MODEL = "llama3.2-vision:11b" }
$env:PYTHONPATH        = "."
$env:PYTHONNOUSERSITE  = "1"
$env:AURELIA_PERSONA_PATH = "seedai\persona_aurelia.md"
$env:AURELIA_BOOTSTRAP_MAX = "4000"
$env:DEV_AUTH          = "true"
$env:GATEWAY_API_KEY   = "ollama"
$env:CORS_ALLOW_ORIGIN = "http://localhost:5173"
$env:VITE_API_URL      = "http://localhost:$BackendPort/api"

# ---- Sync env into core.json (robust) ----
if (!(Test-Path $CoreJson)) { '{}' | Set-Content -Encoding UTF8 $CoreJson }
$j = Get-Content $CoreJson -Raw | ConvertFrom-Json
if ($null -eq $j) { $j = [pscustomobject]@{} }
if (-not ($j.PSObject.Properties.Name -contains 'settings')) {
  $j | Add-Member -NotePropertyName settings -NotePropertyValue ([pscustomobject]@{}) -Force
}
$set = $j.settings
if ($set -isnot [hashtable]) {
  $h=@{}; $set.PSObject.Properties | ForEach-Object { $h[$_.Name] = $_.Value }; $set=$h
}
$set.runtime = @{
  backend  = "http://127.0.0.1:$BackendPort"
  frontend = "http://127.0.0.1:5173"
  ollama   = $env:OLLAMA_BASE_URL
}
$j.settings = $set
($j | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 $CoreJson

function Wait-HttpOk {
  param([string]$Url, [int]$TimeoutSec = 30)
  $sw = [Diagnostics.Stopwatch]::StartNew()
  while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
    try { $r = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec 2; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { return $true } } catch {}
    Start-Sleep -Milliseconds 600
  }
  return $false
}

# ---- Start Ollama ----
if (-not $SkipOllama) {
  Write-Host "[Ollama] starting..."
  Start-Process -WindowStyle Minimized -FilePath "ollama" -ArgumentList "serve" | Out-Null
  Write-Host "[Ollama] waiting for /v1/models ..."
  if (-not (Wait-HttpOk -Url "$($env:OLLAMA_BASE_URL)/v1/models" -TimeoutSec 30)) {
    Write-Warning "[Ollama] did not respond within 30s (continuing)."
  } else {
    Write-Host "[OK] Ollama is responding."
  }
}

# ---- Verify Python ----
try { & $PythonExe --version | Out-Null } catch {
  Write-Error "[ERROR] Python not found: $PythonExe"; exit 1
}

# ---- Start Backend ----
Write-Host "[Backend] starting uvicorn on $BackendHost:$BackendPort ..."
$uvArgs = "-m","uvicorn","gateway.app:app","--host",$BackendHost,"--port",$BackendPort,"--log-level","info"
$pw = @{ FilePath = $PythonExe; ArgumentList = $uvArgs; WorkingDirectory = $RepoRoot; WindowStyle = "Minimized" }
Start-Process @pw | Out-Null
Write-Host "[Backend] waiting for /docs ..."
if (-not (Wait-HttpOk -Url "http://127.0.0.1:$BackendPort/docs" -TimeoutSec 30)) {
  Write-Warning "[Backend] not ready within 30s (frontend may 502 initially)."
} else {
  Write-Host "[OK] Backend is responding."
}

# ---- Start Frontend ----
if (-not (Test-Path (Join-Path $FrontendDir "package.json"))) {
  Write-Warning "[Frontend] $FrontendDir\package.json not found. Skipping."
} else {
  if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "[Frontend] installing dependencies (npm ci)..."
    Push-Location $FrontendDir; try { npm ci } finally { Pop-Location }
  }
  Write-Host "[Frontend] starting dev server on http://localhost:5173 ..."
  $cmd = "cmd"
  $args = "/d","/c","set VITE_API_URL=$($env:VITE_API_URL) && npm run dev"
  $pf = @{ FilePath = $cmd; ArgumentList = $args; WorkingDirectory = (Resolve-Path $FrontendDir); WindowStyle = "Minimized" }
  Start-Process @pf | Out-Null
  if ($OpenBrowser) { Start-Process "http://localhost:5173" | Out-Null }
}

Write-Host ""
Write-Host "=========== AURELIA POINTERS ===========" -ForegroundColor Cyan
Write-Host " GUI:            http://localhost:5173"
Write-Host " API (Swagger):  http://127.0.0.1:$BackendPort/docs"
Write-Host " Health:         http://127.0.0.1:$BackendPort/diag/health"
Write-Host " Models probe:   http://127.0.0.1:$BackendPort/api/models"
Write-Host ""
Write-Host " Memory file:    $CoreJson"
Write-Host ""
Write-Host " OLLAMA_BASE_URL:       $($env:OLLAMA_BASE_URL)"
Write-Host " AURELIA_DEFAULT_MODEL: $($env:AURELIA_DEFAULT_MODEL)"
Write-Host " VITE_API_URL:          $($env:VITE_API_URL)"
Write-Host " CORS_ALLOW_ORIGIN:     $($env:CORS_ALLOW_ORIGIN)"
Write-Host " PYTHONPATH:            $($env:PYTHONPATH)"
Write-Host "========================================" -ForegroundColor Cyan

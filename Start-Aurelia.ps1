<# Start-Aurelia.ps1 — pointers edition
   Launches: backend(8090) + frontend(5173), sets env like run_all,
   shows clickable pointers, and optionally runs the progress reporter.
#>

param(
  [switch]$SkipOllama,
  [switch]$BackendNewWindow,
  [switch]$FrontendNewWindow,
  [switch]$OpenBrowser,
  [switch]$NoReporter    # skip tools/progress_report
)

$ErrorActionPreference = "Stop"

# ----- Paths -------------------------------------------------------------
$RepoRoot    = Split-Path -Path $PSCommandPath -Parent
Set-Location $RepoRoot

$MemoryDir   = Join-Path $RepoRoot "memory"
$LogsDir     = Join-Path $RepoRoot "logs"
$CoreJson    = Join-Path $MemoryDir "core.json"
$FrontendDir = Join-Path $RepoRoot "openweb-ui-frontend"
$Provider    = Join-Path $RepoRoot "provider.json"
$ReporterPy  = Join-Path $RepoRoot "tools\progress_report.py"

# ----- Helpers -----------------------------------------------------------
function Ensure-Dir($p){ if(-not(Test-Path $p)){ New-Item -ItemType Directory -Path $p | Out-Null } }

function Backup-OldMemory {
  Ensure-Dir $MemoryDir
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $archiveDir = Join-Path $MemoryDir ("_archive-" + $stamp)
  Ensure-Dir $archiveDir
  foreach ($n in "comfort.json","identity.json","imprint.json","memory.db","settings.db") {
    $fp = Join-Path $MemoryDir $n
    if (Test-Path $fp) { Move-Item $fp (Join-Path $archiveDir $n) }
  }
  Write-Host "Archived legacy memory → $archiveDir"
}

function New-CoreJson {
  if (Test-Path $CoreJson) { return }
  $obj = [ordered]@{
    meta     = [ordered]@{ version="1.0"; created_at=(Get-Date).ToString("o"); last_boot=(Get-Date).ToString("o"); note="Seed memory file for Aurelia" }
    user     = [ordered]@{ display_name="Lord Shinza"; role="Owner/Co-parent" }
    ai       = [ordered]@{ name="Aurelia"; codename="SeedAI"; persona="Emotionally intelligent, kind, helpful, learning-first"; principles=@(
                  "Be truthful and kind","Prefer memory-first recall before LLM","Ask before crawling or using external sources") }
    settings = [ordered]@{ persistence_enabled=$true; memory_file_format="json" }
    memory   = [ordered]@{ facts=@(); feelings=@(); vocab=@(); imprint=@(); events=@() }
  }
  ($obj | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 $CoreJson
  Write-Host "Created fresh memory\core.json"
}

function Touch-CoreJson {
  if (-not (Test-Path $CoreJson)) { return }
  $j = Get-Content $CoreJson -Raw | ConvertFrom-Json
  $j.meta.last_boot = (Get-Date).ToString("o")
  ($j | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 $CoreJson
}

function Load-ProviderDefaults {
  # Defaults align with README
  $env:OLLAMA_BASE_URL = $env:OLLAMA_BASE_URL   ? $env:OLLAMA_BASE_URL   : "http://127.0.0.1:11434"
  $env:AURELIA_DEFAULT_MODEL = $env:AURELIA_DEFAULT_MODEL ? $env:AURELIA_DEFAULT_MODEL : "llama3.2-vision:11b"
  if (Test-Path $Provider) {
    try {
      $p = Get-Content $Provider -Raw | ConvertFrom-Json
      if ($p.base_url) { $env:OLLAMA_BASE_URL = "$($p.base_url)" }
      if ($p.model)    { $env:AURELIA_DEFAULT_MODEL = "$($p.model)" }
    } catch { Write-Warning "provider.json present but unreadable: $_" }
  }
}

function Start-Ollama {
  if ($SkipOllama) { return }
  try {
    $ok = $false
    try {
      $resp = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -Method GET -TimeoutSec 2
      if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) { $ok = $true }
    } catch {}
    if (-not $ok) {
      Write-Host "Starting Ollama daemon..."
      Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized | Out-Null
      Start-Sleep -Seconds 2
    } else { Write-Host "Ollama is already running." }
  } catch { Write-Warning "Could not start/verify Ollama. Use -SkipOllama to suppress. $_" }
}

function Wait-For($Url, [int]$TimeoutSec = 30) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
    try { $r = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec 2; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { return $true } } catch {}
    Start-Sleep -Milliseconds 600
  }
  return $false
}

function Start-Backend {
  $env:PYTHONPATH = "."
  $env:CORS_ALLOW_ORIGIN = "http://localhost:5173"
  Ensure-Dir $LogsDir
  $args = @("gateway.app:app","--host","0.0.0.0","--port","8090","--log-level","debug")
  Start-Process -FilePath "uvicorn" -ArgumentList $args -WorkingDirectory $RepoRoot
  Write-Host "Backend launching (8090)..."
  if (-not (Wait-For "http://127.0.0.1:8090/docs")) {
    Write-Warning "Backend not ready within timeout (docs)."
  }
}

function Assert-Npm { try { $null = npm -v 2>$null } catch { throw "npm not found. Install Node.js (includes npm) and retry." } }

function Start-Frontend {
  Assert-Npm
  if (-not (Test-Path $FrontendDir)) { throw "Frontend folder not found: $FrontendDir" }

  # Match run_all wiring:
  $env:VITE_API_URL = "http://localhost:8090/api"

  # Install deps if needed
  $nodeModules = Join-Path $FrontendDir "node_modules"
  $hasLock     = Test-Path (Join-Path $FrontendDir "package-lock.json")
  if (-not (Test-Path $nodeModules)) {
    Push-Location $FrontendDir
    try { if ($hasLock) { npm ci } else { npm install } } finally { Pop-Location }
  }

  if ($FrontendNewWindow) {
    Start-Process -FilePath "powershell" -ArgumentList @("-NoProfile","-NoExit","-Command","cd `"$FrontendDir`"; $env:VITE_API_URL='http://localhost:8090/api'; npm run dev") -WorkingDirectory $FrontendDir
  } else {
    Push-Location $FrontendDir
    try { npm run dev } finally { Pop-Location }
  }
  if ($OpenBrowser) { Start-Process "http://localhost:5173" }
}

function Start-ProgressReporter {
  if ($NoReporter) { return }
  if (Test-Path $ReporterPy) {
    try {
      Start-Process -FilePath "python" -ArgumentList "-m","tools.progress_report" -WorkingDirectory $RepoRoot
      Write-Host "Progress reporter started (background)."
    } catch { Write-Warning "Could not start progress reporter: $_" }
  }
}

function Print-Pointers {
  Write-Host ""
  Write-Host "=========== AURELIA POINTERS ===========" -ForegroundColor Cyan
  Write-Host " GUI:            http://localhost:5173"
  Write-Host " API (Swagger):  http://localhost:8090/docs"
  Write-Host " API models:     http://localhost:8090/api/models"
  Write-Host " Diagnostics:    GET  http://localhost:8090/diag/health"
  Write-Host "                 POST http://localhost:8090/diag/memory/test-write"
  Write-Host ""
  Write-Host " Memory file:    $CoreJson"
  Write-Host " Logs dir:       $LogsDir"
  Write-Host ""
  Write-Host " OLLAMA_BASE_URL:      $($env:OLLAMA_BASE_URL)"
  Write-Host " AURELIA_DEFAULT_MODEL: $($env:AURELIA_DEFAULT_MODEL)"
  Write-Host " VITE_API_URL:          $($env:VITE_API_URL)"
  Write-Host " CORS_ALLOW_ORIGIN:     $($env:CORS_ALLOW_ORIGIN)"
  Write-Host " PYTHONPATH:            $($env:PYTHONPATH)"
  Write-Host "========================================" -ForegroundColor Cyan
}
function Write-ReadyBanner {
  param([string]$Msg = "A U R E L I A   O N L I N E")
  Write-Host ""
  Write-Host "========================================" -ForegroundColor Magenta
  Write-Host "  $Msg" -ForegroundColor Green
  Write-Host "  GUI → http://localhost:5173" -ForegroundColor Cyan
  Write-Host "  API → http://localhost:8090/docs" -ForegroundColor Cyan
  Write-Host "========================================" -ForegroundColor Magenta
  try { [console]::Beep(880,150); [console]::Beep(988,150); [console]::Beep(1046,200) } catch {}
}

function Quick-Health {
  $ok = $false
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8090/diag/health" -TimeoutSec 3 -Method GET
    if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 300) { $ok = $true }
  } catch {}
  if ($ok) { Write-Host "Health: OK" -ForegroundColor Green }
  else     { Write-Host "Health: not responding (yet)" -ForegroundColor Yellow }
  return $ok
}

# ----- Run ---------------------------------------------------------------
Ensure-Dir $MemoryDir
Ensure-Dir $LogsDir
Backup-OldMemory
New-CoreJson
Touch-CoreJson

Load-ProviderDefaults   # ← pulls base_url/model from provider.json when present (README mentions both)  # cites defaults
Start-Ollama
Start-Backend
Start-Frontend
Start-ProgressReporter
Print-Pointers

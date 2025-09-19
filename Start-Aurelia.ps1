<#  Start-Aurelia.ps1
    Bootstrap + launch Aurelia (backend 8090 + frontend 5173)

    Usage (from repo root):
      powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Aurelia.ps1
      # Options:
      #   -SkipOllama            -> don't start/verify ollama
      #   -BackendNewWindow      -> run backend in a new window
      #   -FrontendNewWindow     -> run frontend in a new window
      #   -OpenBrowser           -> open http://localhost:5173
#>

param(
  [switch]$SkipOllama,
  [switch]$BackendNewWindow,
  [switch]$FrontendNewWindow,
  [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

# --- Paths ---------------------------------------------------------------
$RepoRoot      = Split-Path -Path $PSCommandPath -Parent
Set-Location $RepoRoot

$MemoryDir     = Join-Path $RepoRoot "memory"
$LogsDir       = Join-Path $RepoRoot "logs"
$CoreJson      = Join-Path $MemoryDir "core.json"

$FrontendDir   = Join-Path $RepoRoot "openweb-ui-frontend"

# --- Helpers -------------------------------------------------------------
function Ensure-Dir($p) {
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}

function Backup-OldMemory {
  Ensure-Dir $MemoryDir
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $archiveDir = Join-Path $MemoryDir ("_archive-" + $stamp)
  Ensure-Dir $archiveDir
  $toMove = @("comfort.json","identity.json","imprint.json","memory.db","settings.db")
  foreach ($n in $toMove) {
    $fp = Join-Path $MemoryDir $n
    if (Test-Path $fp) {
      Move-Item $fp (Join-Path $archiveDir $n)
    }
  }
  Write-Host "Archived old memory files to $archiveDir"
}

function New-CoreJson {
  if (Test-Path $CoreJson) { Write-Host "core.json already exists → leaving as-is."; return }
  $obj = [ordered]@{
    meta = [ordered]@{
      version    = "1.0"
      created_at = (Get-Date).ToString("o")
      last_boot  = (Get-Date).ToString("o")
      note       = "Seed memory file for Aurelia"
    }
    user = [ordered]@{ display_name = "Lord Shinza"; role = "Owner/Co-parent" }
    ai   = [ordered]@{
      name       = "Aurelia"
      codename   = "SeedAI"
      persona    = "Emotionally intelligent, kind, helpful, learning-first"
      principles = @(
        "Be truthful and kind",
        "Prefer memory-first recall before LLM",
        "Ask before crawling or using external sources"
      )
    }
    settings = [ordered]@{ persistence_enabled = $true; memory_file_format = "json" }
    memory   = [ordered]@{ facts=@(); feelings=@(); vocab=@(); imprint=@() }
  }
  ($obj | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 $CoreJson
  Write-Host "Created fresh $CoreJson"
}

function Touch-CoreJson {
  if (-not (Test-Path $CoreJson)) { return }
  $j = Get-Content $CoreJson -Raw | ConvertFrom-Json
  $j.meta.last_boot = (Get-Date).ToString("o")
  ($j | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 $CoreJson
  Write-Host "Stamped core.json (meta.last_boot)."
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
    } else {
      Write-Host "Ollama is already running."
    }
  } catch {
    Write-Warning "Could not start/verify Ollama. Use -SkipOllama to suppress. $_"
  }
}

function Start-Backend {
  $env:PYTHONPATH = "."
  Ensure-Dir $LogsDir
  $args = @("gateway.app:app","--host","0.0.0.0","--port","8090","--log-level","debug")

  if ($BackendNewWindow) {
    Start-Process -FilePath "uvicorn" -ArgumentList $args -WorkingDirectory $RepoRoot
    Write-Host "Backend launched in a new window (port 8090)."
  } else {
    # If we’re also starting the frontend inline, don't block this window:
    if (-not $FrontendNewWindow) {
      Start-Process -FilePath "uvicorn" -ArgumentList $args -WorkingDirectory $RepoRoot
      Write-Host "Backend launched in a background window (port 8090)."
    } else {
      Write-Host "Starting backend in THIS window (Ctrl+C to stop)...`n"
      uvicorn @args
    }
  }
}

function Assert-Npm {
  try {
    $null = npm -v 2>$null
  } catch {
    throw "npm not found. Please install Node.js (which includes npm) and retry."
  }
}

function Start-Frontend {
  if (-not (Test-Path $FrontendDir)) { throw "Frontend folder not found: $FrontendDir" }
  Assert-Npm

  # Auto-install deps if node_modules missing
  $nodeModules = Join-Path $FrontendDir "node_modules"
  $hasLock     = Test-Path (Join-Path $FrontendDir "package-lock.json")
  if (-not (Test-Path $nodeModules)) {
    Push-Location $FrontendDir
    try {
      if ($hasLock) { npm ci } else { npm install }
    } finally { Pop-Location }
  }

  if ($FrontendNewWindow) {
    Start-Process -FilePath "powershell" -ArgumentList @("-NoProfile","-NoExit","-Command","cd `"$FrontendDir`"; npm run dev") -WorkingDirectory $FrontendDir
    Write-Host "Frontend launched in a new window (port 5173)."
  } else {
    Push-Location $FrontendDir
    try {
      Write-Host "Starting frontend dev server on http://localhost:5173 (Ctrl+C to stop)..."
      npm run dev
    } finally { Pop-Location }
  }

  if ($OpenBrowser) {
    Start-Process "http://localhost:5173"
  }
}

# --- Run ----------------------------------------------------------------
Ensure-Dir $MemoryDir
Ensure-Dir $LogsDir
Backup-OldMemory
New-CoreJson
Touch-CoreJson
Start-Ollama
Start-Backend
Start-Frontend

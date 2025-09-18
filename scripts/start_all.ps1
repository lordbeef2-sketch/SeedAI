<#
Starts the canonical launcher `run_all.bat` in a new process.
This wrapper ensures callers (PowerShell users) use the project's launcher.

Usage:
  pwsh> .\scripts\start_all.ps1

The launcher itself will stop stale processes and rotate logs.
#>

$root = Split-Path -Parent $PSScriptRoot
$bat = Join-Path $root '..\run_all.bat' -Resolve
if (-not (Test-Path $bat)) {
    Write-Error "run_all.bat not found at $bat"
    exit 1
}

Start-Process -FilePath $bat -WorkingDirectory (Split-Path $bat) -WindowStyle Normal
Write-Host "Launched run_all.bat (check logs in ./logs)"

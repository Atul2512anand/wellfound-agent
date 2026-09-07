# Windows PowerShell runner for Wellfound Job Agent
# Usage: .\run_windows.ps1 [run|scrape|match|apply]
param([string]$Command="run")

Set-Location $PSScriptRoot
Write-Host "Running: python -m wellfound_agent $Command" -ForegroundColor Cyan
python -m wellfound_agent $Command
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed, trying wellfound-agent command..." -ForegroundColor Yellow
    wellfound-agent $Command
}

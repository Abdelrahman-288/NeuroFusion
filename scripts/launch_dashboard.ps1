param(
    [int]$Port = 8765
)

$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$url = "http://127.0.0.1:$Port/experiments/sampling-comparison-001/index.html"

$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $existing) {
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
        "Set-Location -LiteralPath '$project'; & '$project\.venv-neurofusion\Scripts\python.exe' -m http.server $Port --bind 127.0.0.1"
    )
    Start-Sleep -Milliseconds 700
}

Start-Process $url
Write-Host "NeuroFusion dashboard: $url"
Write-Host "Project directory: $project"
Write-Host "Stop the local server later with: Get-NetTCPConnection -LocalPort $Port | Stop-Process -Id {`$_.OwningProcess}"

param([int]$Port = 8766)
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$url = "http://127.0.0.1:$Port"
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 5
    if ($health.app -ne 'NeuroFusion local viewer') { throw 'Port is occupied by another service.' }
} else {
    $logs = Join-Path $project 'experiments/local-viewer'
    New-Item -ItemType Directory -Path $logs -Force | Out-Null
    $viewerProcess = Start-Process -FilePath "$project\.venv-neurofusion\Scripts\python.exe" -ArgumentList @('-u', 'scripts/serve_viewer.py', '--port', "$Port") -WorkingDirectory $project -WindowStyle Hidden -RedirectStandardOutput "$logs/server.log" -RedirectStandardError "$logs/server-errors.log" -PassThru
    $viewerProcess.Id | Set-Content "$logs/server.pid"
    $ready = $false
    for ($attempt=0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 500
        try { $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 2; if ($health.app -eq 'NeuroFusion local viewer') { $ready=$true; break } } catch {}
    }
    if (-not $ready) { throw "Viewer did not start. Inspect $logs/server-errors.log" }
}
Start-Process $url
Write-Host "NeuroFusion viewer: $url"
Write-Host 'For a foreground server you can stop with Ctrl+C, run: .\.venv-neurofusion\Scripts\python.exe scripts/serve_viewer.py'

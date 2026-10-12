param([switch]$Bootstrap)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$reviewArgs = @(
    (Join-Path $PSScriptRoot 'serve_collaboration.py'),
    '--acquisition', (Join-Path $projectRoot 'data\active-learning-review-acquisition'),
    '--storage', (Join-Path $projectRoot 'data\active-learning-review'),
    '--development-partitions', (Join-Path $projectRoot 'experiments\ucsf-specialist-plan-001\partitions.json'),
    '--port', '8781'
)
if ($Bootstrap) { $reviewArgs += '--bootstrap' }
& (Join-Path $projectRoot '.venv-neurofusion\Scripts\python.exe') @reviewArgs
exit $LASTEXITCODE

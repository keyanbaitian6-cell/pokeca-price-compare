$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$Python = if (Test-Path -LiteralPath $VenvPython) { $VenvPython } else { 'python' }

# Keep the source tree importable even when this script is launched by Task Scheduler.
$PythonPathParts = @((Join-Path $ProjectRoot 'src'))
$LocalDeps = Join-Path $ProjectRoot '.deps'
if (Test-Path -LiteralPath $LocalDeps) {
    $PythonPathParts += $LocalDeps
}
if ($env:PYTHONPATH) {
    $PythonPathParts += $env:PYTHONPATH
}
$env:PYTHONPATH = $PythonPathParts -join ';'

$CommandArgs = @('-m', 'card_price_compare', '--output-dir', (Join-Path $ProjectRoot 'data'))
if ($env:CARD_PRICE_OUTPUT_SHEET_ID -and $env:GOOGLE_APPLICATION_CREDENTIALS) {
    $CommandArgs += @(
        '--google-spreadsheet-id', $env:CARD_PRICE_OUTPUT_SHEET_ID,
        '--google-credentials', $env:GOOGLE_APPLICATION_CREDENTIALS
    )
}

Push-Location $ProjectRoot
try {
    & $Python @CommandArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}

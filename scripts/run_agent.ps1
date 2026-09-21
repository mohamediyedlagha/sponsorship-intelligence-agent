# ============================================================
# Sponsorship Intelligence Agent
# Scheduled execution script
# ============================================================

$ProjectPath = Split-Path -Parent $PSScriptRoot

Set-Location $ProjectPath

$PythonPath = Join-Path `
    $ProjectPath `
    ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonPath)) {

    Write-Error `
        "Python virtual environment not found: $PythonPath"

    exit 1
}

Write-Host ""
Write-Host "Starting Sponsorship Intelligence Agent..."
Write-Host "Project: $ProjectPath"
Write-Host ""

& $PythonPath -m src.main

$ExitCode = $LASTEXITCODE

Write-Host ""

if ($ExitCode -eq 0) {

    Write-Host `
        "Sponsorship Intelligence Agent completed successfully."

}
else {

    Write-Error `
        "Sponsorship Intelligence Agent failed with exit code $ExitCode."
}

exit $ExitCode
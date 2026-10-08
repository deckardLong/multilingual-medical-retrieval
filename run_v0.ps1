param(
    [string]$Start = $(if ($env:START) { $env:START } else { "s1" }),
    [string]$PythonPath = $env:PYTHON
)

$ErrorActionPreference = "Stop"
$steps = @(
    "s1_chunk",
    "s2_embed",
    "s3_retrieve",
    "s4_rerank",
    "s5_select",
    "s6_build_submit",
    "s7_validate"
)

$startIndex = -1
for ($index = 0; $index -lt $steps.Count; $index++) {
    if ($steps[$index].StartsWith($Start, [System.StringComparison]::OrdinalIgnoreCase)) {
        $startIndex = $index
        break
    }
}

if ($startIndex -lt 0) {
    throw "Start step '$Start' not found. Valid steps: $($steps -join ', ')."
}

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $localVenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    $parentVenvPython = Join-Path (Split-Path -Parent $PSScriptRoot) "venv\Scripts\python.exe"

    if (Test-Path $localVenvPython) {
        $PythonPath = $localVenvPython
    } elseif (Test-Path $parentVenvPython) {
        $PythonPath = $parentVenvPython
    } else {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pythonCommand) {
            throw "Python was not found. Create .venv or pass -PythonPath."
        }
        $PythonPath = $pythonCommand.Source
    }
}

if (-not (Test-Path $PythonPath)) {
    throw "Python executable not found at '$PythonPath'."
}

Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force -Path "workspace\runs" | Out-Null
Write-Host "Python: $PythonPath"

for ($index = $startIndex; $index -lt $steps.Count; $index++) {
    $step = $steps[$index]
    Write-Host "=== $step  $(Get-Date -Format 'HH:mm:ss') ==="
    & $PythonPath "src\$step.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Step '$step' failed with exit code $LASTEXITCODE."
    }
}

Write-Host "Done. Submission archive: workspace\runs\submission.zip"

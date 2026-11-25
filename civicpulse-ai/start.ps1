$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

function Resolve-Python {
    $VenvPy = Join-Path $BackendDir ".venv\Scripts\python.exe"
    if (Test-Path $VenvPy) { return $VenvPy }

    $Candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
    )
    foreach ($c in $Candidates) {
        if (Test-Path $c) { return $c }
    }

    $Cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($Cmd -and $Cmd.Source -notlike "*WindowsApps*") { return $Cmd.Source }

    throw "Python 3.11+ interpreter not found."
}

$PythonExe = Resolve-Python
Write-Host "Using Python: $PythonExe" -ForegroundColor Cyan

& $PythonExe -c "import fastapi, reportlab, pandas, numpy, sklearn, openpyxl" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
    & $PythonExe -m pip install -r (Join-Path $BackendDir "requirements.txt")
}

$SampleCsv = Join-Path $BackendDir "sample_data\civicpulse_complaints_sample.csv"
if (-not (Test-Path $SampleCsv)) {
    & $PythonExe (Join-Path $BackendDir "sample_data_generator.py") --rows 620
}

Write-Host "Starting CivicPulse AI FastAPI backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
$BackendProc = Start-Process -FilePath $PythonExe -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $BackendDir -PassThru -NoNewWindow

try {
    foreach ($NodeCandidate in @(
        (Join-Path $RootDir ".tools\nodejs"),
        (Join-Path (Split-Path -Parent $RootDir) "ps158-workload-assistant\.tools\nodejs")
    )) {
        if (Test-Path (Join-Path $NodeCandidate "npm.cmd")) {
            $env:PATH = "$NodeCandidate;$env:PATH"
            break
        }
    }

    $NpmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    $DistIndex = Join-Path $FrontendDir "dist\index.html"

    if ($NpmCmd) {
        if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
            Write-Host "Installing frontend npm dependencies..." -ForegroundColor Yellow
            Push-Location $FrontendDir
            & $NpmCmd.Source install
            Pop-Location
        }
        Write-Host "Starting CivicPulse AI React UI on http://localhost:5173 ..." -ForegroundColor Green
        Push-Location $FrontendDir
        & $NpmCmd.Source run dev
        Pop-Location
    } elseif (Test-Path $DistIndex) {
        Write-Host "Serving built CivicPulse AI dashboard at http://127.0.0.1:8000" -ForegroundColor Cyan
        Wait-Process -Id $BackendProc.Id
    } else {
        Write-Warning "Node/npm not detected. FastAPI docs available at http://127.0.0.1:8000/docs"
        Wait-Process -Id $BackendProc.Id
    }
} finally {
    if ($BackendProc -and -not $BackendProc.HasExited) {
        Stop-Process -Id $BackendProc.Id -Force
    }
}


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

    throw "Python 3.11+ interpreter not found. Please install Python 3.12 or create backend\.venv."
}

$PythonExe = Resolve-Python
Write-Host "Using Python: $PythonExe" -ForegroundColor Cyan

# Ensure backend packages are available
& $PythonExe -c "import fastapi, reportlab, pandas, numpy" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing backend Python dependencies..." -ForegroundColor Yellow
    & $PythonExe -m pip install -r (Join-Path $BackendDir "requirements.txt")
}

# Generate default sample CSV if missing
$SampleCsv = Join-Path $BackendDir "sample_data\municipal_service_requests.csv"
if (-not (Test-Path $SampleCsv)) {
    & $PythonExe (Join-Path $BackendDir "generate_sample_data.py") --rows 640
}

Write-Host "Starting FastAPI backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
$BackendProc = Start-Process -FilePath $PythonExe -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $BackendDir -PassThru -NoNewWindow

try {
    $LocalNodeDir = Join-Path $RootDir ".tools\nodejs"
    if (Test-Path (Join-Path $LocalNodeDir "npm.cmd")) {
        $env:PATH = "$LocalNodeDir;$env:PATH"
    }
    $NpmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    $DistIndex = Join-Path $FrontendDir "dist\index.html"

    if ($NpmCmd) {
        if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
            Write-Host "Installing frontend npm packages..." -ForegroundColor Yellow
            Push-Location $FrontendDir
            & $NpmCmd.Source install
            Pop-Location
        }
        Write-Host "Starting Vite React dashboard on http://localhost:5173 ..." -ForegroundColor Green
        Push-Location $FrontendDir
        & $NpmCmd.Source run dev
        Pop-Location
    } elseif (Test-Path $DistIndex) {
        Write-Host "Node/npm not found; serving built React frontend via FastAPI at http://127.0.0.1:8000" -ForegroundColor Cyan
        Wait-Process -Id $BackendProc.Id
    } else {
        Write-Warning "Node.js / npm not detected and frontend/dist is not built. Backend API docs available at http://127.0.0.1:8000/docs"
        Wait-Process -Id $BackendProc.Id
    }
} finally {
    if ($BackendProc -and -not $BackendProc.HasExited) {
        Write-Host "Stopping FastAPI backend..." -ForegroundColor Yellow
        Stop-Process -Id $BackendProc.Id -Force
    }
}


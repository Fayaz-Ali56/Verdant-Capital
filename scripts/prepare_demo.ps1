# Run from the project root. Native command failures stop the script explicitly.
$ErrorActionPreference = "Stop"
if (!(Test-Path "requirements-dev.txt")) { throw "Run from the repository root" }
if (!(Test-Path ".venv")) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Python 3.12 virtual environment creation failed" }
}
$python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
function Invoke-ProjectPython {
    & $python @args
    if ($LASTEXITCODE -ne 0) { throw "Python command failed with exit code $LASTEXITCODE" }
}
Invoke-ProjectPython -m pip install --upgrade pip
Invoke-ProjectPython -m pip install -r requirements-dev.txt -c requirements-lock.txt
Invoke-ProjectPython scripts/check.py
Invoke-ProjectPython -m challenge.c02_rare_event
Invoke-ProjectPython -m challenge.c06_explainability
Invoke-ProjectPython -m challenge.c13_cost_sensitive
Invoke-ProjectPython -m data.feedback_backtest
Invoke-ProjectPython -m orchestrator.graph
Invoke-ProjectPython -m streamlit run app.py

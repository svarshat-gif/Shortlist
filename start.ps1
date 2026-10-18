$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) { $pythonCommand = Get-Command py -ErrorAction SilentlyContinue }
$localPython = Join-Path $env:LOCALAPPDATA 'Python\pythoncore-3.14-64\python.exe'
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    if (Test-Path -LiteralPath $localPython) { & $localPython -m venv .venv }
    elseif ($pythonCommand) { & $pythonCommand.Source -m venv .venv }
    else { throw 'Install Python 3.11 or newer, then run this command again.' }
    if ($LASTEXITCODE -ne 0) { throw 'Python setup did not finish.' }
}
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
$nodeExe = Join-Path $PSScriptRoot '.tools\node.exe'
if (-not (Test-Path -LiteralPath $nodeExe)) {
    if ($nodeCommand) { $nodeExe = $nodeCommand.Source }
    else { throw 'Install Node.js 20 or newer, then run this command again.' }
}
$env:Path = (Split-Path -Parent $nodeExe) + ';' + $env:Path
$npmCli = Join-Path $PSScriptRoot '.tools\package\bin\npm-cli.js'
if (-not (Test-Path -LiteralPath $npmCli)) { $npmCli = Join-Path (Split-Path -Parent $nodeExe) 'node_modules\npm\bin\npm-cli.js' }
& $pythonExe -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependencies could not be installed. Check your connection and try again.' }
& $nodeExe $npmCli ci --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { throw 'Website dependencies could not be installed. Check your connection and try again.' }
& $pythonExe -m scripts.create_samples
if ($LASTEXITCODE -ne 0) { throw 'Sample CVs could not be prepared.' }
& $nodeExe $npmCli run build
if ($LASTEXITCODE -ne 0) { throw 'The website build did not finish.' }
Write-Host "`nShortlist is ready at http://127.0.0.1:8000`nDemo sign-in: recruiter@demo.com / demo123`nPress Ctrl+C to stop.`n"
& $pythonExe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --no-access-log

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$interprete = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $interprete)) {
    python -m venv ..\.venv
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno virtual.' }
}
& $interprete -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron comprobar las dependencias.' }
& $interprete preparar_bd.py
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar PostgreSQL. Revisa .env.' }
& $interprete servidor_wsgi.py

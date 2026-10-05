# Builds a single windowed EXE (no console window): dist\Theaterplanung.exe
# Usage: .\build.ps1                          (uses "python" from PATH)
#        .\build.ps1 -Python "C:\Path\To\Python\python.exe"   (example path, adjust to your own)
param([string]$Python = "python")

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

& $Python -m pip install -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

& $Python -m PyInstaller --noconfirm --clean --windowed --onefile `
    --name Theaterplanung `
    --hidden-import babel.numbers `
    --specpath build `
    main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Write-Host "Done: dist\Theaterplanung.exe"

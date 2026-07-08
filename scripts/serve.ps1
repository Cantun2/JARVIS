# Lance le backend JARVIS (API + WebSocket sur http://127.0.0.1:8000) sous Windows.
# Règle l'encodage UTF-8 et ajoute Ollama au PATH automatiquement.
# Usage :  .\scripts\serve.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:PYTHONUTF8 = "1"
$ollama = Join-Path $env:LOCALAPPDATA "Programs\Ollama"
if (Test-Path $ollama) { $env:PATH = "$env:PATH;$ollama" }

Write-Host "JARVIS -> http://127.0.0.1:8000  (Ctrl+C pour arreter)" -ForegroundColor Cyan
& "$root\.venv\Scripts\python.exe" -m jarvis serve

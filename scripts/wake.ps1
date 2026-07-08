# JARVIS — réveil en une commande (Windows).
#
# Démarre le backend (API + WebSocket + UI si buildée), attend qu'il réponde,
# déclenche éventuellement la séquence de réveil ATLAS, puis ouvre le navigateur.
#
# Usage :
#   .\scripts\wake.ps1            # démarre et ouvre l'UI
#   .\scripts\wake.ps1 -Wake      # + joue la séquence de réveil ATLAS
#   .\scripts\wake.ps1 -NoBrowser # ne pas ouvrir le navigateur
#
# Deux modes d'UI :
#   - Prod (mono-processus) : `cd ui && npm run build` puis mettre JARVIS_UI_DIST=ui/dist
#     dans .env → l'UI est servie sur http://127.0.0.1:8000 par le backend.
#   - Dev (hot reload) : ce script lance aussi `npm run dev` (Vite) sur :5173 si l'UI
#     n'est pas buildée/servie par le backend.
param(
    [switch]$Wake,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:PYTHONUTF8 = "1"
$ollama = Join-Path $env:LOCALAPPDATA "Programs\Ollama"
if (Test-Path $ollama) { $env:PATH = "$env:PATH;$ollama" }

$py = Join-Path $root ".venv\Scripts\python.exe"
$apiBase = "http://127.0.0.1:8000"

# Le backend sert-il l'UI lui-même ? (JARVIS_UI_DIST défini et présent)
$servesUi = $false
$envFile = Join-Path $root ".env"
if (Test-Path $envFile) {
    $uiLine = Select-String -Path $envFile -Pattern '^\s*JARVIS_UI_DIST\s*=' -ErrorAction SilentlyContinue
    if ($uiLine) { $servesUi = $true }
}

Write-Host "JARVIS — démarrage du backend..." -ForegroundColor Cyan
Start-Process -FilePath $py -ArgumentList "-m", "jarvis", "serve" -WorkingDirectory $root -WindowStyle Minimized

# Attendre que l'API réponde (santé).
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        $h = Invoke-RestMethod -Uri "$apiBase/api/health" -TimeoutSec 2
        if ($h.version) { $ready = $true; break }
    } catch { Start-Sleep -Milliseconds 500 }
}
if (-not $ready) {
    Write-Host "Le backend n'a pas répondu à temps. Voir la fenêtre du serveur." -ForegroundColor Red
    exit 1
}
Write-Host "Backend prêt (mode=$($h.mode), inférence=$($h.inference_backend))." -ForegroundColor Green

# UI : dev (Vite) si le backend ne sert pas l'UI.
$uiUrl = $apiBase
if (-not $servesUi) {
    Write-Host "UI en mode dev (Vite :5173)..." -ForegroundColor Cyan
    Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory (Join-Path $root "ui") -WindowStyle Minimized
    $uiUrl = "http://localhost:5173"
    Start-Sleep -Seconds 2
}

# Réveil ATLAS optionnel.
if ($Wake) {
    Write-Host "Séquence de réveil ATLAS..." -ForegroundColor Cyan
    try {
        Invoke-RestMethod -Method Post -Uri "$apiBase/api/agents/ATLAS/run" -Body '{}' -ContentType "application/json" -TimeoutSec 30 | Out-Null
        Write-Host "ATLAS: réveil déclenché." -ForegroundColor Green
    } catch {
        Write-Host "ATLAS indisponible (normal si Gmail non branché)." -ForegroundColor Yellow
    }
}

if (-not $NoBrowser) { Start-Process $uiUrl }
Write-Host "JARVIS est réveillé → $uiUrl" -ForegroundColor Cyan

# MZ BUILDING - Lancement du backend (API) sous Windows / PowerShell
# Usage : double-clic sur START_BACKEND.bat, ou  .\START_BACKEND.ps1  (option -Reload pour le développement)
param([switch]$Reload)
$racine  = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $racine "backend"
Set-Location $backend
Write-Host "=== MZ BUILDING - Backend ===" -ForegroundColor Cyan

function Arreter($message) {
    Write-Host ""
    Write-Host $message -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

if (-not (Test-Path ".env")) {
    Arreter "Le fichier backend\.env est introuvable. Copiez .env.example (a la racine du projet) vers backend\.env puis remplissez-le (voir INSTALLATION.md, etape 5)."
}

if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "Creation de l'environnement Python (premiere fois, 1 a 2 minutes)..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) { Arreter "Python est introuvable. Installez Python 3.12 (voir INSTALLATION.md, etape 1)." }
}
. .\venv\Scripts\Activate.ps1

python -c "import fastapi, uvicorn, sqlalchemy, asyncpg" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installation des dependances Python (premiere fois, quelques minutes)..."
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Arreter "L'installation des dependances a echoue. Copiez le message d'erreur ci-dessus." }
}

$occupe = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($occupe) {
    Arreter "Le port 8000 est deja utilise (un ancien serveur tourne encore). Fermez l'autre fenetre du backend, ou voir INSTALLATION.md, section Problemes courants."
}

Write-Host "Backend disponible sur  http://localhost:8000/docs  (Ctrl+C pour arreter)" -ForegroundColor Green
if ($Reload) { python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload }
else         { python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 }
Read-Host "Le serveur s'est arrete. Appuyez sur Entree pour fermer"

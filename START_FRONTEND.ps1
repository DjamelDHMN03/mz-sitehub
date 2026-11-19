# MZ BUILDING - Lancement du frontend (interface web) sous Windows / PowerShell
# Usage : double-clic sur START_FRONTEND.bat, ou  .\START_FRONTEND.ps1
$racine   = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontend = Join-Path $racine "frontend"
Set-Location $frontend
Write-Host "=== MZ BUILDING - Frontend ===" -ForegroundColor Cyan

function Arreter($message) {
    Write-Host ""
    Write-Host $message -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

node --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { Arreter "Node.js est introuvable. Installez Node.js LTS (voir INSTALLATION.md, etape 1)." }

if (-not (Test-Path "node_modules")) {
    Write-Host "Installation des dependances (premiere fois, quelques minutes)..."
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Nouvel essai avec --legacy-peer-deps..." -ForegroundColor Yellow
        npm install --legacy-peer-deps
        if ($LASTEXITCODE -ne 0) { Arreter "L'installation a echoue. Copiez le message d'erreur ci-dessus." }
    }
}

$occupe = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($occupe) {
    Arreter "Le port 5173 est deja utilise (un ancien frontend tourne encore). Fermez l'autre fenetre du frontend puis relancez. Le backend n'accepte que http://localhost:5173."
}

Write-Host "Interface disponible sur  http://localhost:5173  (Ctrl+C pour arreter)" -ForegroundColor Green
npm run dev -- --port 5173 --strictPort
Read-Host "Le serveur s'est arrete. Appuyez sur Entree pour fermer"

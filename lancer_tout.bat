@echo off
title MZ-SITEHUB Launcher Global
echo Lancement du Backend FastAPI...
start cmd /k "cd backend && uvicorn app.main:app --reload"

echo Lancement du Frontend Vite...
start cmd /k "cd frontend && npm run dev"

echo Tout est lance ! Vous pouvez fermer cette fenetre.
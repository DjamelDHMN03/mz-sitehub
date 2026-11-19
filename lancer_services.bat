@echo off
cd /d "%~dp0"
start /b python -m uvicorn backend.app.main:app --port 8000
cd frontend
call npm run dev
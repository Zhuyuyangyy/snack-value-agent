@echo off
cd /d %~dp0\..

start "FashionMix Backend" cmd /k "cd backend && uvicorn app:app --port 8001 --reload"
timeout /t 2 /nobreak > nul
start "FashionMix Frontend" cmd /k "cd .. && python -m http.server 8000"

echo.
echo ===========================================
echo Frontend: http://localhost:8000/frontend/index.html
echo Backend:  http://localhost:8001
echo ===========================================
echo Press any key to close launcher (servers keep running)
pause > nul
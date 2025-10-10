@echo off
echo Restarting FastAPI server to load new code changes...
echo.

REM Kill any existing Python processes that might be running the server
taskkill /f /im python.exe 2>nul

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start the server
echo Starting FastAPI server...
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
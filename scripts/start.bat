@echo off
REM Digital Twin startup script for Windows

echo Starting Digital Twin services...

REM Check if Redis is running (you'll need to install Redis for Windows)
tasklist /FI "IMAGENAME eq redis-server.exe" 2>NUL | find /I /N "redis-server.exe">NUL
if "%ERRORLEVEL%"=="1" (
    echo Redis not found. Please start Redis manually or install it.
    echo You can download Redis for Windows from: https://github.com/microsoftarchive/redis/releases
)

REM Check if PostgreSQL is running
tasklist /FI "IMAGENAME eq postgres.exe" 2>NUL | find /I /N "postgres.exe">NUL
if "%ERRORLEVEL%"=="1" (
    echo PostgreSQL not found. Please start PostgreSQL manually.
    echo Make sure PostgreSQL is installed and running.
)

REM Start Celery worker in background
echo Starting Celery worker...
start /B celery -A app.core.celery worker --loglevel=info

REM Start the FastAPI application
echo Starting FastAPI application...
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
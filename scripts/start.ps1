# Digital Twin startup script for Windows PowerShell

Write-Host "Starting Digital Twin services..." -ForegroundColor Green

# Check if Redis is running
$redisProcess = Get-Process -Name "redis-server" -ErrorAction SilentlyContinue
if (-not $redisProcess) {
    Write-Host "Redis not found. Please start Redis manually." -ForegroundColor Yellow
    Write-Host "You can download Redis for Windows from: https://github.com/microsoftarchive/redis/releases" -ForegroundColor Yellow
}

# Check if PostgreSQL is running
$postgresProcess = Get-Process -Name "postgres" -ErrorAction SilentlyContinue
if (-not $postgresProcess) {
    Write-Host "PostgreSQL not found. Please start PostgreSQL manually." -ForegroundColor Yellow
    Write-Host "Make sure PostgreSQL is installed and running." -ForegroundColor Yellow
}

# Start Celery worker in background
Write-Host "Starting Celery worker..." -ForegroundColor Green
Start-Process -FilePath "celery" -ArgumentList "-A", "app.core.celery", "worker", "--loglevel=info" -WindowStyle Hidden

# Wait a moment for Celery to start
Start-Sleep -Seconds 2

# Start the FastAPI application
Write-Host "Starting FastAPI application..." -ForegroundColor Green
Write-Host "API will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API docs will be available at: http://localhost:8000/docs" -ForegroundColor Cyan

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
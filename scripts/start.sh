#!/bin/bash

# Digital Twin startup script

echo "Starting Digital Twin services..."

# Start Redis (if not running)
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
fi

# Start PostgreSQL (if not running)
if ! pgrep -x "postgres" > /dev/null; then
    echo "Starting PostgreSQL..."
    # This command varies by system
    # sudo systemctl start postgresql  # For systemd
    # brew services start postgresql   # For macOS with Homebrew
fi

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A app.core.celery worker --loglevel=info --detach

# Start the FastAPI application
echo "Starting FastAPI application..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
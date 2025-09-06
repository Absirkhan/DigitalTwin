# Local Development Setup (Windows, No Docker)

This guide will help you set up the Digital Twin project for local development on Windows without using Docker.

## Prerequisites

### 1. Python 3.11+
Make sure you have Python 3.11 or higher installed:
```cmd
python --version
```

### 2. PostgreSQL
Download and install PostgreSQL from: https://www.postgresql.org/download/windows/
- During installation, remember your postgres user password
- Default port is 5432

### 3. Redis (Optional but recommended)
Download Redis for Windows from: https://github.com/microsoftarchive/redis/releases
- Extract and run `redis-server.exe`
- Or use Windows Subsystem for Linux (WSL) to run Redis

### 4. Chrome/Chromium Browser
Required for meeting automation features.

## Setup Steps

### 1. Install Python Dependencies
```cmd
cd DigitalTwin
pip install -r requirements.txt
```

### 2. Set up Database
Create a PostgreSQL database:
```sql
-- Connect to PostgreSQL as postgres user
CREATE DATABASE digitaltwin;
```

### 3. Configure Environment
Copy and edit the environment file:
```cmd
copy .env.example .env
```

Edit `.env` file with your settings:
- Update `DATABASE_URL` with your PostgreSQL credentials
- Add your OpenAI API key
- Generate a secure `SECRET_KEY`

### 4. Run Setup Script
```cmd
python scripts/setup.py
```

This will:
- Create necessary directories
- Copy environment file (if needed)
- Install dependencies
- Run database migrations

### 5. Start Services

#### Option A: Use PowerShell Script (Recommended)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

#### Option B: Use Batch Script
```cmd
scripts/start.bat
```

#### Option C: Manual Start
Start each service manually:

1. **Start Redis** (if installed):
   ```cmd
   redis-server
   ```

2. **Start Celery Worker**:
   ```cmd
   celery -A app.core.celery worker --loglevel=info
   ```

3. **Start FastAPI Application**:
   ```cmd
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Accessing the Application

Once running, you can access:
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Development Workflow

### Running Tests
```cmd
pytest tests/
```

### Database Migrations
```cmd
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head
```

### Code Quality
```cmd
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

## Troubleshooting

### Common Issues

1. **PostgreSQL Connection Error**
   - Make sure PostgreSQL is running
   - Check your DATABASE_URL in .env
   - Verify database exists

2. **Redis Connection Error**
   - Install Redis for Windows or use WSL
   - Make sure Redis is running on port 6379

3. **Import Errors**
   - Make sure you're in the DigitalTwin directory
   - Verify all dependencies are installed: `pip install -r requirements.txt`

4. **Port Already in Use**
   - Change the port in the uvicorn command: `--port 8001`
   - Or kill the process using the port

### Windows-Specific Notes

- Use PowerShell for better script execution
- Some audio libraries might require additional Windows-specific setup
- Chrome WebDriver will be automatically managed by webdriver-manager

## Next Steps

1. Update your `.env` file with real API keys and credentials
2. Test the API endpoints using the documentation at `/docs`
3. Upload voice samples to train your digital twin
4. Configure meeting platform integrations (Zoom, Teams)

## Development Tips

- Use the `--reload` flag with uvicorn for automatic reloading during development
- Check logs in the `logs/` directory for debugging
- Use the API documentation at `/docs` to test endpoints interactively
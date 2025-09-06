# Manual Installation Guide

If the automatic setup fails due to dependency conflicts, follow these steps:

## Step 1: Upgrade pip

```cmd
python -m pip install --upgrade pip
```

## Step 2: Install Core Dependencies

```cmd
pip install fastapi uvicorn pydantic python-multipart
pip install sqlalchemy alembic psycopg2-binary redis
pip install python-jose[cryptography] passlib[bcrypt]
pip install python-dotenv schedule celery httpx aiofiles python-dateutil requests
pip install structlog prometheus-client
```

## Step 3: Install AI/ML Dependencies (Optional)

```cmd
pip install openai
pip install langchain langchain-community
pip install transformers sentence-transformers
pip install chromadb
```

## Step 4: Install Voice Processing (Optional - may fail on Windows)

```cmd
pip install speechrecognition pydub librosa soundfile
```

## Step 5: Install Meeting Integration

```cmd
pip install selenium webdriver-manager websockets
```

## Step 6: Install Development Tools (Optional)

```cmd
pip install pytest pytest-asyncio black flake8 mypy
```

## Alternative: Install without version constraints

If you're still having issues, try installing without specific versions:

```cmd
pip install --no-deps fastapi uvicorn pydantic
pip install --no-deps sqlalchemy alembic psycopg2-binary
# Continue with other packages...
```

## Torch Installation (if needed)

For PyTorch, you might need to install from the official site:

```cmd
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

## Skip Problematic Packages

You can skip packages that cause issues and install them later:

- `pyaudio` - Often problematic on Windows
- `torch`/`torchaudio` - Large downloads, install separately if needed
- Voice processing libraries - Can be installed later when needed

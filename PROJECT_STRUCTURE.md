# Digital Twin Project Structure

## Complete File Structure

```
DigitalTwin/
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules
├── Dockerfile                       # Docker container configuration
├── docker-compose.yml              # Multi-container Docker setup
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Python project configuration
├── alembic.ini                      # Database migration configuration
├── README.md                        # Project documentation
├── PROJECT_STRUCTURE.md             # This file
│
├── app/                             # Main application package
│   ├── __init__.py
│   ├── main.py                      # FastAPI application entry point
│   │
│   ├── api/                         # API layer
│   │   ├── __init__.py
│   │   └── v1/                      # API version 1
│   │       ├── __init__.py
│   │       ├── api.py               # Main API router
│   │       └── endpoints/           # API endpoint handlers
│   │           ├── __init__.py
│   │           ├── auth.py          # Authentication endpoints
│   │           ├── users.py         # User management endpoints
│   │           ├── digital_twins.py # Digital twin endpoints
│   │           ├── meetings.py      # Meeting management endpoints
│   │           └── voice.py         # Voice processing endpoints
│   │
│   ├── core/                        # Core application components
│   │   ├── __init__.py
│   │   ├── config.py                # Application configuration
│   │   ├── database.py              # Database connection and session
│   │   └── celery.py                # Background task configuration
│   │
│   ├── models/                      # Database models (SQLAlchemy)
│   │   ├── __init__.py
│   │   ├── user.py                  # User model
│   │   ├── digital_twin.py          # Digital twin model
│   │   ├── meeting.py               # Meeting model
│   │   └── voice_sample.py          # Voice sample model
│   │
│   ├── schemas/                     # Pydantic schemas for API
│   │   ├── __init__.py
│   │   ├── auth.py                  # Authentication schemas
│   │   ├── user.py                  # User schemas
│   │   ├── digital_twin.py          # Digital twin schemas
│   │   └── meeting.py               # Meeting schemas
│   │
│   └── services/                    # Business logic layer
│       ├── __init__.py
│       ├── auth.py                  # Authentication service
│       ├── user.py                  # User management service
│       ├── digital_twin.py          # Digital twin service
│       ├── meeting.py               # Meeting service
│       ├── voice.py                 # Voice processing service
│       ├── voice_processing.py      # Voice cloning and TTS
│       ├── meeting_automation.py    # Meeting bot automation
│       └── ai_responses.py          # RAG-powered AI responses
│
├── alembic/                         # Database migrations
│   ├── env.py                       # Alembic environment configuration
│   ├── script.py.mako               # Migration script template
│   └── versions/                    # Migration files (auto-generated)
│
├── tests/                           # Test suite
│   ├── __init__.py
│   └── test_main.py                 # Basic application tests
│
├── scripts/                         # Utility scripts
│   ├── setup.py                     # Project setup script
│   └── start.sh                     # Service startup script
│
├── models/                          # AI model storage
│   └── weights/                     # Trained model weights
│
├── recordings/                      # Audio file storage
│   ├── temp/                        # Temporary audio files
│   ├── uploads/                     # User uploaded audio
│   └── generated/                   # AI generated audio
│
├── data/                            # Data storage
│   └── vectordb/                    # Vector database for RAG
│
└── logs/                            # Application logs
```

## Key Components

### 1. FastAPI Application (`app/main.py`)
- Main application entry point
- CORS middleware configuration
- API router inclusion
- Lifespan events for startup/shutdown

### 2. API Layer (`app/api/`)
- RESTful API endpoints
- Request/response handling
- Authentication and authorization
- Input validation

### 3. Database Models (`app/models/`)
- SQLAlchemy ORM models
- Database table definitions
- Relationships between entities

### 4. Business Logic (`app/services/`)
- Core business logic
- External service integrations
- Background task definitions
- AI/ML processing

### 5. Configuration (`app/core/`)
- Application settings
- Database configuration
- Background task setup

## Technology Stack

### Backend Framework
- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: SQL toolkit and ORM
- **Alembic**: Database migration tool
- **Pydantic**: Data validation using Python type annotations

### Database & Caching
- **PostgreSQL**: Primary database
- **Redis**: Caching and message broker

### Background Tasks
- **Celery**: Distributed task queue
- **Redis**: Message broker for Celery

### AI/ML Libraries
- **OpenAI**: GPT models for text generation
- **LangChain**: Framework for LLM applications
- **ChromaDB**: Vector database for RAG
- **Transformers**: Hugging Face transformers
- **PyTorch**: Deep learning framework

### Voice Processing
- **librosa**: Audio analysis
- **soundfile**: Audio file I/O
- **speechrecognition**: Speech-to-text
- **pydub**: Audio manipulation

### Meeting Automation
- **Selenium**: Web browser automation
- **webdriver-manager**: WebDriver management

### Development Tools
- **Docker**: Containerization
- **pytest**: Testing framework
- **black**: Code formatting
- **flake8**: Code linting
- **mypy**: Static type checking

## Getting Started

1. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Setup**
   ```bash
   alembic upgrade head
   ```

4. **Start Services**
   ```bash
   # Using Docker Compose
   docker-compose up -d
   
   # Or manually
   uvicorn app.main:app --reload
   celery -A app.core.celery worker --loglevel=info
   ```

5. **Access API Documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Development Workflow

1. **Create Feature Branch**
2. **Implement Changes**
3. **Add Tests**
4. **Run Quality Checks**
   ```bash
   black app/
   flake8 app/
   mypy app/
   pytest tests/
   ```
5. **Create Migration** (if needed)
   ```bash
   alembic revision --autogenerate -m "Description"
   ```
6. **Submit Pull Request**

## Deployment

### Docker Deployment
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Manual Deployment
1. Set up production environment variables
2. Configure reverse proxy (nginx)
3. Set up SSL certificates
4. Configure monitoring and logging
5. Set up database backups

This structure provides a solid foundation for building a scalable AI-powered meeting automation system with proper separation of concerns, comprehensive testing, and production-ready deployment options.
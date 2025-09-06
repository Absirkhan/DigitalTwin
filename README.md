# Digital Twin - AI Meeting Automation

AI Digital Twin for Meeting Automation - Intelligent workplace productivity solution that creates personalized AI representatives to attend meetings on behalf of users. Features voice cloning, behavioral analysis, automated meeting joining, real-time participation, and comprehensive documentation with RAG-powered responses.

## Features

- **Digital Twin Creation**: Create personalized AI representatives with custom personalities and communication styles
- **Voice Cloning**: Train custom voice models using user audio samples
- **Meeting Automation**: Automatically join Zoom, Teams, and other meeting platforms
- **Real-time Participation**: AI-powered responses during meetings using RAG (Retrieval-Augmented Generation)
- **Meeting Documentation**: Automatic transcription, summarization, and action item extraction
- **Behavioral Learning**: Continuous learning from user interactions and preferences

## Architecture

```
DigitalTwin/
├── app/                          # Main application
│   ├── api/                      # API endpoints
│   │   └── v1/
│   │       ├── endpoints/        # Route handlers
│   │       └── api.py           # API router
│   ├── core/                     # Core configuration
│   │   ├── config.py            # Settings
│   │   ├── database.py          # Database setup
│   │   └── celery.py            # Background tasks
│   ├── models/                   # Database models
│   ├── schemas/                  # Pydantic schemas
│   ├── services/                 # Business logic
│   └── main.py                  # FastAPI app
├── alembic/                      # Database migrations
├── tests/                        # Test suite
├── scripts/                      # Utility scripts
├── models/                       # AI model storage
├── recordings/                   # Audio files
├── data/                         # Vector database
└── docker-compose.yml           # Container orchestration
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- Chrome/Chromium (for meeting automation)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd DigitalTwin
   ```

2. **Run setup script**
   ```bash
   python scripts/setup.py
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start services**
   ```bash
   # Using Docker Compose (recommended)
   docker-compose up -d
   
   # Or manually
   ./scripts/start.sh
   ```

### API Documentation

Once running, visit:
- API Documentation: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Usage

### 1. Create a Digital Twin

```python
import requests

# Register user
response = requests.post("http://localhost:8000/api/v1/auth/register", json={
    "email": "user@example.com",
    "full_name": "John Doe",
    "password": "secure_password"
})

# Login
response = requests.post("http://localhost:8000/api/v1/auth/login", data={
    "username": "user@example.com",
    "password": "secure_password"
})
token = response.json()["access_token"]

# Create digital twin
headers = {"Authorization": f"Bearer {token}"}
response = requests.post("http://localhost:8000/api/v1/digital-twins/", 
    headers=headers,
    json={
        "name": "My Digital Twin",
        "description": "Professional meeting assistant",
        "communication_style": "professional",
        "personality_traits": {
            "tone": "friendly",
            "expertise": "technical"
        }
    }
)
```

### 2. Train Voice Model

```python
# Upload voice samples
with open("voice_sample.wav", "rb") as f:
    files = {"audio_file": f}
    response = requests.post(
        f"http://localhost:8000/api/v1/digital-twins/{twin_id}/train-voice",
        headers=headers,
        files=files
    )
```

### 3. Schedule Meeting

```python
# Schedule meeting
response = requests.post("http://localhost:8000/api/v1/meetings/",
    headers=headers,
    json={
        "title": "Team Standup",
        "meeting_url": "https://zoom.us/j/123456789",
        "platform": "zoom",
        "scheduled_time": "2024-01-15T10:00:00Z",
        "digital_twin_id": twin_id,
        "auto_join": True
    }
)
```

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/digitaltwin

# Redis
REDIS_URL=redis://localhost:6379

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Meeting Platforms
ZOOM_CLIENT_ID=your-zoom-client-id
ZOOM_CLIENT_SECRET=your-zoom-client-secret
```

### Meeting Platform Setup

#### Zoom
1. Create a Zoom App at https://marketplace.zoom.us/
2. Get Client ID and Secret
3. Configure OAuth redirect URLs

#### Microsoft Teams
1. Register app in Azure AD
2. Configure API permissions
3. Get Client ID and Secret

## Development

### Running Tests

```bash
pytest tests/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### Code Quality

```bash
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

## Deployment

### Docker

```bash
# Build and run
docker-compose up -d

# Scale services
docker-compose up -d --scale celery=3
```

### Production Considerations

- Use environment-specific configuration
- Set up proper logging and monitoring
- Configure SSL/TLS certificates
- Set up database backups
- Use a reverse proxy (nginx)
- Configure rate limiting

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/login` - Login user

### Digital Twins
- `POST /api/v1/digital-twins/` - Create digital twin
- `GET /api/v1/digital-twins/` - List user's digital twins
- `GET /api/v1/digital-twins/{id}` - Get digital twin
- `PUT /api/v1/digital-twins/{id}` - Update digital twin
- `DELETE /api/v1/digital-twins/{id}` - Delete digital twin
- `POST /api/v1/digital-twins/{id}/train-voice` - Train voice model

### Meetings
- `POST /api/v1/meetings/` - Schedule meeting
- `GET /api/v1/meetings/` - List meetings
- `GET /api/v1/meetings/{id}` - Get meeting details
- `PUT /api/v1/meetings/{id}` - Update meeting
- `DELETE /api/v1/meetings/{id}` - Delete meeting
- `POST /api/v1/meetings/{id}/join` - Join meeting with twin

### Voice
- `POST /api/v1/voice/upload` - Upload voice sample
- `POST /api/v1/voice/generate` - Generate voice response
- `GET /api/v1/voice/samples/{twin_id}` - Get voice samples

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the API docs at `/docs`
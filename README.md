# DigitalTwin - AI-Powered Meeting Assistant

## 🌟 Project Overview

DigitalTwin is an intelligent meeting automation platform built as a Final Year Project (FYP). The system provides automated meeting management capabilities including bot-based meeting participation, video recording, transcription, and AI-powered summarization using custom-trained models.

### ✅ Implemented Features

- 🤖 **Automated Meeting Bots** - AI bots that join meetings via Recall.ai
- 📹 **Video Recording & Storage** - High-quality MP4 recordings with local storage
- 📝 **Meeting Transcriptions** - Real-time transcript generation and formatting
- ⚡ **Real-Time WebSocket Transcription** - Live transcript streaming with <100ms latency
- 🧠 **AI Summarization** - Custom fine-tuned FLAN-T5 model for meeting summaries
- 📅 **Google Calendar Integration** - OAuth-based calendar synchronization
- 🔐 **Secure Authentication** - Google OAuth 2.0 implementation
- 🗄️ **Database Management** - PostgreSQL with comprehensive schema
- 📊 **Meeting Analytics** - Transcript statistics and processing

### 🔮 Planned Features

- 🎯 **Enhanced Digital Twin** - More sophisticated AI representation
- ✅ **RAG Module (Completed)** - Ultra-low-latency context retrieval for voice assistants
- 🔄 **RAG Integration (In Progress)** - Integrate RAG module with main FastAPI application
- 📱 **Mobile Application** - Cross-platform mobile interface
- 📈 **Advanced Analytics** - Detailed meeting insights and reporting

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   External APIs │
│   (Web/Mobile)  │◄──►│   (FastAPI)     │◄──►│   (Recall AI)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │   PostgreSQL    │    │   Google APIs   │
                    │   Database      │    │   (OAuth, Cal)  │
                    └─────────────────┘    └─────────────────┘
```

### Technology Stack

**Backend Framework:**
- **FastAPI** - Modern Python web framework for API development
- **SQLAlchemy** - Database ORM for PostgreSQL interaction
- **Alembic** - Database migration management
- **Pydantic** - Data validation and serialization

**Database & Storage:**
- **PostgreSQL** - Primary database for user data and meeting records
- **Local File Storage** - Video recordings and transcript storage

**Authentication & Security:**
- **Google OAuth 2.0** - Secure user authentication
- **JWT Tokens** - Session management and API access

**AI & External Services:**
- **Recall.ai** - Meeting bot deployment and recording service
- **Fine-tuned FLAN-T5** - Custom AI model for meeting summarization
- **Google Calendar API** - Calendar integration and event management
- **Google Gmail API** - Email processing capabilities

**Development & Deployment:**
- **Uvicorn** - ASGI server for FastAPI
- **Python 3.11+** - Core programming language
- **Git** - Version control with feature branching

## 📁 Project Structure

```
DigitalTwin/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── api/                      # API routes
│   │   ├── __init__.py
│   │   └── v1/                   # API version 1
│   │       ├── __init__.py
│   │       ├── api.py            # Main API router
│   │       └── endpoints/        # Individual route handlers
│   │           ├── auth.py       # Authentication endpoints
│   │           ├── calendar.py   # Calendar management
│   │           ├── meetings.py   # Meeting operations
│   │           ├── users.py      # User management
│   │           └── voice.py      # Voice processing
│   ├── core/                     # Core application components
│   │   ├── __init__.py
│   │   ├── config.py            # Application configuration
│   │   ├── database.py          # Database setup
│   │   └── celery.py            # Background task configuration
│   ├── models/                   # Database models
│   │   ├── __init__.py
│   │   ├── bot.py               # Bot model with recording fields
│   │   ├── calendar_event.py    # Calendar events
│   │   ├── email.py             # Email processing
│   │   ├── meeting.py           # Meeting management
│   │   └── user.py              # User authentication
│   ├── schemas/                  # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── auth.py              # Authentication schemas
│   │   ├── digital_twin.py      # Digital twin schemas
│   │   ├── meeting.py           # Meeting and recording schemas
│   │   └── user.py              # User schemas
│   └── services/                 # Business logic services
│       ├── __init__.py
│       ├── ai_responses.py      # AI response generation
│       ├── auth.py              # Authentication service
│       ├── calendar.py          # Calendar integration
│       ├── digital_twin.py      # Digital twin management
│       ├── meeting.py           # Meeting operations
│       ├── meeting_automation.py # Automated meeting handling
│       ├── recall_service.py    # Recall.ai integration
│       ├── recording_service.py # Video recording management
│       ├── summary_service.py   # AI summarization
│       ├── user.py              # User management
│       ├── voice.py             # Voice processing
│       └── voice_processing.py  # Audio processing
├── alembic/                      # Database migrations
│   ├── env.py                   # Migration environment
│   ├── script.py.mako           # Migration template
│   └── versions/                # Migration files
│       ├── 001_initial_schema.py
│       ├── 002_add_missing_meeting_columns.py
│       ├── 003_update_user_oauth.py
│       └── 004_add_recording_fields.py
├── data/                         # Data storage
│   └── vectordb/                # Vector database files
├── logs/                         # Application logs
├── models/                       # AI model files
│   └── weights/                 # Model weights
├── recordings/                   # Video recordings
│   ├── generated/               # Processed recordings
│   ├── temp/                    # Temporary files
│   └── uploads/                 # User uploads
├── scripts/                      # Utility scripts
│   ├── init_db.py              # Database initialization
│   ├── setup.py                # Project setup
│   └── verify_schema.py        # Schema validation
├── static/                       # Static files
│   ├── auth_error.html         # Error page
│   ├── auth_success.html       # Success page
│   └── login.html              # Login page
├── summary_model/               # AI summarization model
│   ├── README.md
│   ├── summary_inference_minimal.py
│   └── summary_model_minimal.py
├── transcripts/                 # Meeting transcripts
├── rag_module/                  # RAG system for voice assistants
│   ├── rag/                    # Core RAG implementation
│   │   ├── embedder.py         # Text embedding (all-MiniLM-L6-v2)
│   │   ├── faiss_store.py      # FAISS vector store
│   │   ├── retriever.py        # Context retrieval
│   │   ├── memory_manager.py   # Session memory
│   │   ├── profile_manager.py  # User profiling
│   │   ├── prompt_builder.py   # Token budget management
│   │   └── pipeline.py         # Main orchestrator
│   ├── tests/                  # Comprehensive test suite
│   │   ├── test_faiss_store.py
│   │   ├── test_retriever.py
│   │   ├── test_profile.py
│   │   └── test_pipeline.py
│   ├── data/                   # User data storage
│   │   └── users/              # Per-user FAISS indexes
│   ├── demo.py                 # Full system demonstration
│   └── benchmark.py            # Performance benchmarking
├── alembic.ini                 # Alembic configuration
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
└── README.md                   # This file
```

## 🚀 Project Setup

### System Requirements

- Python 3.11+
- PostgreSQL 12+
- Redis 5.0+ (required for real-time transcription)
- Google Cloud Console account (for OAuth and Calendar APIs)
- Recall.ai API account (for meeting bots and recording)

### Quick Setup

### 1. Clone and Setup Environment

```bash
git clone https://github.com/Absirkhan/DigitalTwin.git
cd DigitalTwin

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Configuration

```bash
# Create PostgreSQL database
createdb digitaltwin

# Apply database migrations
alembic upgrade head
```

### 3. Redis Installation (Required for Real-Time Transcription)

**Windows:**
1. Download Redis for Windows from: https://github.com/tporadowski/redis/releases
2. Download and run: `Redis-x64-5.0.14.1.msi`
3. Follow the installer (default settings are fine)
4. Redis will auto-start as a Windows service

**Mac:**
```bash
brew install redis
brew services start redis
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**Docker:**
```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

**Verify Redis is running:**
```bash
redis-cli ping
# Expected output: PONG
```

**Note for Windows users:** If `redis-cli` is not recognized, use the full path:
```bash
& "C:\Program Files\Redis\redis-cli.exe" ping
```

Or use the wrapper script provided in the project:
```bash
.\redis-cli.bat ping
```

See [REDIS_SETUP_WINDOWS.md](REDIS_SETUP_WINDOWS.md) for detailed Windows installation troubleshooting.

### 4. Environment Setup

Configure your `.env` file with required API keys and database connection:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost/digitaltwin

# Google OAuth (required for authentication)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Recall.ai (required for meeting bots)
RECALL_API_KEY=your-recall-api-key
RECALL_BASE_URL=https://us-east-1.recall.ai/api/v1

# Redis (required for real-time transcription)
REDIS_URL=redis://localhost:6379

# Real-Time Transcription WebSocket
REALTIME_WEBHOOK_URL=http://localhost:8000/api/v1/realtime/webhook/recall
WEBSOCKET_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# Security
SECRET_KEY=your-super-secret-key-here
```

### 5. API Setup

**Google APIs:**
1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create project and enable Google Calendar API
3. Create OAuth 2.0 credentials
4. Add redirect URI: `http://localhost:8000/api/v1/auth/google/callback`

**Recall.ai:**
1. Sign up at [Recall.ai](https://recall.ai)
2. Get API key from dashboard
3. Add to environment configuration

### 6. Start the Application

```bash
uvicorn app.main:app --reload
```

**Expected startup output:**
```
✅ Database initialized
✅ Redis pub/sub service initialized
✅ DigitalTwin application started successfully!
📡 Real-time transcription webhook: http://localhost:8000/api/v1/realtime/webhook/recall
🔌 WebSocket endpoint: ws://localhost:8000/api/v1/realtime/ws/transcript/{meeting_id}
```

Access the application at: http://localhost:8000

**For real-time transcription documentation, see:**
- [QUICKSTART_REALTIME.md](QUICKSTART_REALTIME.md) - 5-minute setup guide
- [REALTIME_TRANSCRIPTION.md](REALTIME_TRANSCRIPTION.md) - Complete documentation

## 🔧 System Implementation

### 1. Authentication System

Secure user authentication using Google OAuth 2.0 with JWT token management.

**Implementation:**
- Google OAuth 2.0 integration for passwordless authentication
- JWT tokens for session management
- Automatic token refresh handling
- Secure token storage in PostgreSQL database

**Key Components:**
- `app/api/v1/endpoints/auth.py` - Authentication API endpoints
- `app/services/auth.py` - Authentication business logic
- `app/models/user.py` - User database model

### 2. Meeting Management System

Comprehensive meeting lifecycle management from scheduling to post-meeting processing.

**Implementation:**
- Meeting scheduling and metadata storage
- Integration with Google Calendar for automatic meeting detection
- Meeting status tracking (scheduled, in-progress, completed)
- User-specific meeting data isolation

**Key Components:**
- `app/api/v1/endpoints/meetings.py` - Meeting management endpoints
- `app/services/meeting.py` - Meeting operations and business logic
- `app/models/meeting.py` - Meeting database model

### 3. Recall.ai Bot Integration

Automated meeting participation using Recall.ai's bot service for recording and transcription.

**Implementation:**
- Automatic bot deployment to meeting URLs
- Real-time meeting recording (audio and video)
- Live transcription generation
- Meeting status monitoring and webhook handling

**Key Components:**
- `app/services/recall_service.py` - Recall.ai API integration
- `app/services/recording_service.py` - Recording management
- `app/models/bot.py` - Bot tracking and status management

### 4. AI Summarization

The AI system uses a custom fine-tuned FLAN-T5 model to generate intelligent summaries and extract action items from meeting transcripts.

**Key Files:**
- `app/services/summary_service.py` - AI summarization service
- `summary_model/` - Fine-tuned FLAN-T5 model and inference code
- `summary_model/summary_model_minimal.py` - Model implementation
- `summary_model/summary_inference_minimal.py` - Inference pipeline

**Features:**
- **Fine-tuned FLAN-T5 Model** - Custom-trained for meeting summarization
- **Intelligent meeting summaries** - Context-aware summary generation
- **Action item extraction** - Automated identification of tasks and follow-ups
- **Participant analysis** - Speaker identification and contribution tracking
- **Local model deployment** - No external API dependencies for summarization

**AI Processing Pipeline:**
```
1. Raw transcript received from Recall.ai
2. Text preprocessing and cleaning
3. Fine-tuned FLAN-T5 model processes content
4. Generates structured summary with action items
5. Extracts key discussion points and decisions
6. Stores processed results in database
```

### 5. RAG Module - Voice Assistant Context Retrieval

The RAG (Retrieval Augmented Generation) module provides ultra-low-latency context retrieval for voice assistant applications. It's a **standalone system** located in `/rag_module/`.

**Key Files:**
- `rag_module/rag/` - Core implementation (7 modules)
- `rag_module/tests/` - Comprehensive test suite
- `rag_module/demo.py` - Full system demonstration
- `rag_module/benchmark.py` - Performance benchmarking

**Features:**
- **FAISS-based vector store** - Sub-millisecond retrieval target (~15ms measured)
- **Per-user data isolation** - Separate FAISS indexes for each user
- **Token budget enforcement** - Strict 2150 token limit for LLM prompts
- **User profiling** - Automatic speaking style analysis and personalization
- **Session memory** - In-memory storage of last 6 messages
- **CPU-only operation** - No GPU dependencies
- **Offline-capable** - Falls back to word-based token estimation

**Processing Pipeline:**
```
User Query → Embedder (all-MiniLM-L6-v2, 384-dim)
           ↓
    FAISS Retriever (top-k similarity search, threshold filtering)
           ↓
    Profile Manager (user style analysis)
           ↓
    Prompt Builder (token budget enforcement)
           ↓
    Assembled LLM Prompt (ready for voice assistant)
```

**Usage:**
```python
from rag.pipeline import RAGPipeline

# Initialize and use
pipeline = RAGPipeline(base_path="rag_module/data/users")
result = pipeline.process_message("user123", "How do I fix this error?")

# Returns: prompt, retrieved_context, token_breakdown, retrieval_latency_ms
```

**Performance Metrics:**
- Retrieval latency: ~15ms average (target: <1ms, overhead from embedding generation)
- Token budget compliance: 100% (all test cases within 2150 limit)
- Storage efficiency: ~70KB per 100 exchanges

**Running Tests:**
```bash
cd rag_module
python demo.py              # Full demonstration with 2 sessions
python benchmark.py         # Performance benchmarking
python tests/test_pipeline.py  # Integration tests
```

**Note:** Currently standalone - integration with main FastAPI app planned for future release.

### 6. Google Calendar Integration

Automatic meeting detection and synchronization with Google Calendar.

**Implementation:**
- OAuth-based Google Calendar API integration
- Automatic meeting URL extraction from calendar events
- Meeting participant detection
- Bidirectional sync (read calendar events, create meetings)

**Key Components:**
- `app/services/calendar.py` - Calendar operations
- `app/models/calendar_event.py` - Calendar event storage
- `app/api/v1/endpoints/calendar.py` - Calendar API endpoints

### 7. Database Schema & Management

Comprehensive PostgreSQL database design supporting all system features.

**Implementation:**
- User management with OAuth token storage
- Meeting lifecycle tracking
- Bot status and recording metadata
- Calendar event synchronization
- Future RAG system preparation

**Key Components:**
- `alembic/versions/` - Database migration history
- `app/models/` - SQLAlchemy database models
- `DATABASE_SCHEMA.md` - Complete schema documentation

## 🗄️ Current Database Schema

The system uses PostgreSQL with the following core tables:

### Core Tables (Implemented)

1. **Users** - User accounts with Google OAuth integration
2. **Meetings** - Meeting metadata, status, and processing results
3. **Bots** - Recall.ai bot tracking with recording capabilities
4. **Calendar Events** - Google Calendar synchronization data
5. **Emails** - Email processing for meeting notifications

### Future Extensions (Planned)

6. **Documents** - Document storage for RAG system
7. **Document Chunks** - Text chunks for vector search
8. **Embeddings** - Vector embeddings for semantic search
9. **RAG Queries** - Query logging and analytics

*See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for complete technical documentation.*

## 📡 API Overview

The system provides RESTful APIs for all core functionality:

### Authentication APIs
```
POST /api/v1/auth/google/login     # Get Google OAuth URL
GET  /api/v1/auth/google/callback  # Handle OAuth callback
GET  /api/v1/auth/me               # Get current user info
POST /api/v1/auth/logout           # User logout
```

### Meeting Management APIs
```
GET    /api/v1/meetings/           # List user meetings
POST   /api/v1/meetings/           # Create new meeting
GET    /api/v1/meetings/{id}       # Get meeting details
PUT    /api/v1/meetings/{id}       # Update meeting
DELETE /api/v1/meetings/{id}       # Delete meeting
POST   /api/v1/meetings/join       # Join meeting with bot
```

### Recording & Transcript APIs
```
GET  /api/v1/meetings/recording/{bot_id}         # Get recording status
POST /api/v1/meetings/recording/{bot_id}/update  # Update recording status
POST /api/v1/meetings/recording/{bot_id}/download # Download recording
GET  /api/v1/meetings/transcript/{bot_id}           # Get transcript
GET  /api/v1/meetings/transcript/{bot_id}/formatted # Get formatted transcript
```

### Calendar Integration APIs
```
GET  /api/v1/calendar/events      # List calendar events
POST /api/v1/calendar/sync        # Sync with Google Calendar
```

*Complete API documentation available at: http://localhost:8000/docs*

## 🔄 Background Tasks

The system uses Celery for background task processing.

**Key Tasks:**
- Meeting monitoring and auto-joining
- Transcript processing
- AI summarization
- Calendar synchronization
- Recording cleanup

**Task Configuration:**
```python
# app/core/celery.py
from celery import Celery

celery_app = Celery(
    "digitaltwin",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)
```

## 🎯 Project Achievements

### Technical Implementation
- **Full-stack web application** using FastAPI and PostgreSQL
- **OAuth 2.0 authentication** with Google integration
- **External API integration** with Recall.ai for meeting automation
- **Custom AI model deployment** using fine-tuned FLAN-T5
- **Real-time data processing** for meeting transcripts and recordings
- **Scalable database design** with migration system

### Core Functionality Delivered
- ✅ User authentication and session management
- ✅ Meeting scheduling and management
- ✅ Automated bot deployment to meetings
- ✅ Video recording and storage
- ✅ Real-time transcription processing
- ✅ AI-powered meeting summarization
- ✅ Calendar integration and synchronization
- ✅ RAG module for voice assistant context retrieval
- ✅ Comprehensive API documentation

### Security & Data Management
- **Secure authentication** using Google OAuth 2.0
- **Token-based session management** with JWT
- **Encrypted data storage** for sensitive information
- **User data isolation** and privacy protection
- **API access control** and request validation

## 🔮 Future Development

### Planned Enhancements

**RAG Integration (Phase 2 - In Progress)**
- ✅ Standalone RAG module completed (FAISS-based, sub-millisecond retrieval)
- 🔄 Integration with main FastAPI application
- 🔄 REST API endpoints for RAG operations
- 🔄 Database storage option (PostgreSQL vector extension)
- 🔄 Redis caching layer for performance
- 🔄 Metrics and monitoring dashboard

**Advanced AI Features**
- Real-time meeting insights and alerts
- Sentiment analysis of meeting conversations
- Automatic speaker identification and tracking
- Multi-language support for global teams

**Enhanced User Experience**
- Mobile application development
- Real-time notifications and alerts
- Advanced analytics and reporting dashboard
- Customizable meeting templates and automation rules

**Enterprise Features**
- Team collaboration and sharing
- Administrator dashboard and controls
- Advanced security and compliance features
- Integration with enterprise tools (Slack, Microsoft Teams)

## 🏆 Project Impact

### Problem Solved
The DigitalTwin system addresses the growing need for automated meeting management in hybrid work environments. By providing intelligent meeting participation, recording, and summarization, it helps professionals save time and improve meeting productivity.

### Technical Innovation
- **Custom AI Model**: Fine-tuned FLAN-T5 specifically for meeting summarization
- **Seamless Integration**: Combined multiple external APIs (Google, Recall.ai) into cohesive system
- **Scalable Architecture**: Designed for future expansion with RAG and advanced AI features

### Learning Outcomes
- Advanced Python web development with FastAPI
- Database design and management with PostgreSQL
- OAuth 2.0 implementation and security best practices
- External API integration and error handling
- AI model fine-tuning and deployment
- Real-time data processing and storage

## � Project Information

**Project Type:** Final Year Project (FYP)  
**Academic Year:** 2024-2025  
**Technology Focus:** AI-Powered Meeting Automation  
**Primary Language:** Python  
**Framework:** FastAPI  

### Technical Specifications
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Authentication:** Google OAuth 2.0 + JWT
- **AI Model:** Fine-tuned FLAN-T5 for summarization
- **External APIs:** Recall.ai, Google Calendar, Google Gmail
- **Deployment:** Local development with Uvicorn

### Repository Structure
- **Main Branch:** `main` - Stable release version
- **Feature Branch:** `feature/recording` - Video recording implementation
- **Documentation:** Complete API docs and database schema

## 🙏 Acknowledgments

- **Recall.ai** - For providing the meeting bot and recording infrastructure
- **Google APIs** - For OAuth authentication and Calendar integration
- **HuggingFace** - For the FLAN-T5 model and fine-tuning resources
- **FastAPI Community** - For the excellent web framework and documentation

---

**DigitalTwin** - An AI-powered meeting automation platform designed to enhance productivity through intelligent meeting management, recording, and summarization.
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
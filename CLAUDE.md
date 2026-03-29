# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DigitalTwin is an AI-powered meeting automation platform (FYP project). The system combines FastAPI backend with Next.js frontend to provide automated meeting participation, recording, transcription, and AI-powered summarization using a custom fine-tuned FLAN-T5 model.

## Development Commands

### Backend (Python/FastAPI)

```bash
# Environment setup
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Database operations
createdb digitaltwin
alembic upgrade head                              # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
alembic downgrade -1                              # Rollback one migration
alembic current                                   # Check current version

# Redis (required for real-time features)
# Windows: Use full path or add to PATH (see REDIS_SETUP_WINDOWS.md)
& "C:\Program Files\Redis\redis-cli.exe" ping     # Test Redis connection
redis-cli ping                                    # If Redis is in PATH

# Run development server (requires Redis running)
uvicorn app.main:app --reload                     # http://localhost:8000
uvicorn app.main:app --reload --port 8001         # Custom port

# Background task worker (Celery)
# Windows (use solo pool to avoid multiprocessing issues)
celery -A app.core.celery worker --loglevel=info --pool=solo
# Linux/Mac (use prefork for better concurrency)
celery -A app.core.celery worker --loglevel=info

# Utility scripts
python scripts/init_db.py                         # Initialize database
python test_summarization.py                      # Test AI model
python test_calendar_webhook.py                   # Test calendar sync
```

### Frontend (Next.js/TypeScript)

```bash
cd frontend/web_gui

# Install dependencies
npm install

# Development
npm run dev     # http://localhost:3000

# Production
npm run build   # Build for production
npm start       # Run production server

# Code quality
npm run lint    # ESLint checks
```

## Architecture

### System Structure

This is a **client-server architecture** with async background processing and real-time features:

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js)                                             │
│  - React Components                                             │
│  - WebSocket Client (useRealtimeTranscript hook)                │
│  - HTTP Client (lib/api/client.ts)                              │
└───────────────┬──────────────────────┬──────────────────────────┘
                │ HTTP (REST)          │ WebSocket
                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend API (FastAPI)                                          │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ REST Endpoints │  │ WebSocket    │  │ Recall.ai        │   │
│  │ /api/v1/*      │  │ Manager      │  │ Webhook Handler  │   │
│  └────────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
│           │                  │                    │             │
│           ▼                  ▼                    ▼             │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Services Layer                                        │   │
│  │  - recall_service.py (Recall.ai integration)           │   │
│  │  - redis_pubsub.py (Message broker)                    │   │
│  │  - websocket_manager.py (Connection manager)           │   │
│  │  - auth.py, meeting.py, summarization.py, etc.         │   │
│  └──────┬─────────────────────┬───────────────────────────┘   │
└─────────┼─────────────────────┼───────────────────────────────┘
          │                     │
          ▼                     ▼
┌──────────────────┐   ┌──────────────────┐
│   PostgreSQL     │   │   Redis Pub/Sub  │
│   - users        │   │   - Channels:    │
│   - meetings     │   │     meeting:*    │
│   - bots         │   │   - Celery Queue │
│   - calendars    │   │                  │
└──────────────────┘   └──────────────────┘

          │
          ▼
┌──────────────────┐
│  Local FLAN-T5   │
│  Model (best_    │
│  model/)         │
└──────────────────┘

External Services:
┌────────────────┐     ┌─────────────────┐
│  Recall.ai     │     │  Google OAuth   │
│  - Bots        │     │  - Calendar API │
│  - Recording   │     │  - Gmail API    │
│  - Transcripts │     │                 │
│  - Webhooks    │     │                 │
└────────────────┘     └─────────────────┘
```

**Key characteristics:**
- **OAuth-only authentication** (Google OAuth 2.0, no password management)
- **Fully async/await** implementation throughout backend
- **Real-time transcription** via WebSocket and Redis pub/sub (~600ms latency)
- **Local AI model deployment** (fine-tuned FLAN-T5 in `best_model/`)
- **Background task processing** with Celery for long-running operations
- **External service integration** with Recall.ai for meeting bots and recordings

### Technology Stack

**Backend:**
- FastAPI 0.104.1 (ASGI async framework)
- SQLAlchemy 1.4.48 (ORM) + Alembic (migrations)
- PostgreSQL (primary database)
- Redis 5.0.1 (real-time pub/sub, background task queue)
- Celery 5.4.0 (background task worker)
- Transformers, PyTorch, PEFT (AI/ML)
- aiohttp 3.9.1 (async HTTP client)

**Frontend:**
- Next.js 16.0.1 (React 19.2.0)
- TypeScript 5
- Tailwind CSS 4
- Native WebSocket API (real-time features)

**External Services:**
- Google OAuth 2.0, Calendar API, Gmail API
- Recall.ai (meeting bots, recording, and real-time transcription service)

## Code Organization

### Backend Structure (`/app`)

**Core Components:**
- `app/main.py` - Application entry point, FastAPI app initialization
- `app/core/config.py` - Pydantic settings from environment variables
- `app/core/database.py` - SQLAlchemy setup, session management
- `app/core/celery.py` - Background task configuration

**API Layer (`app/api/v1/endpoints/`):**
- `auth.py` - OAuth login/callback, JWT tokens, user session
- `meetings.py` - Meeting CRUD, bot join/leave, status tracking
- `calendar.py` - Google Calendar sync and event management
- `summarization.py` - AI summary generation endpoints
- `users.py` - User profile management
- `realtime.py` - **Real-time transcription** WebSocket and webhook endpoints
- `tts.py` - **Voice cloning and TTS** endpoints with caching and async synthesis
- `rag.py` - **RAG/LLM AI assistant** endpoints with context retrieval

**Service Layer (`app/services/`):**
- `recall_service.py` (65KB) - **Most critical service** - Recall.ai bot management, recording, transcription, webhook handling
- `redis_pubsub.py` - Redis pub/sub message broker for real-time features
- `websocket_manager.py` - WebSocket connection manager for per-meeting transcript streams
- `summarization.py` - FLAN-T5 model inference, action item extraction
- `auth.py` - OAuth flow, JWT generation, token refresh
- `calendar.py` - Google Calendar integration
- `meeting.py` - Meeting business logic
- `meeting_automation.py` - Auto-join scheduling logic
- `meeting_status_monitor.py` - **Auto-store transcripts in RAG** when meeting completes
- `tts_service.py` - **NeuTTS Nano voice cloning** with model pre-warming
- `tts_cache.py` - **Redis caching for TTS** responses (<50ms cache hits)
- `tts_tasks.py` - **Celery background tasks** for async TTS synthesis
- `rag_service.py` - **RAG/LLM integration** singleton service with pre-warming

**Data Layer:**
- `app/models/` - SQLAlchemy ORM models (user, meeting, bot, calendar_event, email)
- `app/schemas/` - Pydantic request/response validation schemas

### Frontend Structure (`/frontend/web_gui/app`)

**Next.js App Router:**
- `app/page.tsx` - Landing page
- `app/login/page.tsx` - Login page
- `app/auth/callback/page.tsx` - OAuth callback handler
- `app/dashboard/` - Protected dashboard pages (meetings, recordings, transcripts, profile)

**API Integration:**
- `lib/api/client.ts` - HTTP client with auth token management
- `lib/api/auth.ts` - Authentication API calls
- `lib/hooks/useAuth.ts` - React auth hook
- `lib/hooks/useRealtimeTranscript.ts` - **Real-time WebSocket hook** for live transcription

**UI Components:**
- `app/components/` - Reusable UI components
- `app/components/RealtimeTranscript.tsx` - **Real-time transcript viewer** with WebSocket connection
- `app/components/VoiceSetup.tsx` - **Voice profile management** with recording, preview, and caching
- `app/components/RagQuery.tsx` - **RAG/LLM AI assistant** query interface with metrics
- `app/contexts/` - React context providers (theme, auth)
- `app/styles/` - CSS modules and Tailwind utilities

## Database Schema

**Core tables (implemented):**
1. **users** - OAuth tokens, profile, `bot_name` (custom name for meeting bot), `enable_backend_tasks`, `has_voice_profile` (TTS)
2. **meetings** - Full lifecycle tracking, `transcript` (text), `summary` (text), `action_items` (JSON array)
3. **bots** - Recall.ai bot status, `recording_url`, `video_url`, `meeting_id` FK
4. **calendar_events** - Google Calendar sync, meeting URL extraction
5. **emails** - Email processing data

**Planned tables (RAG system):**
- documents, document_chunks, embeddings, rag_queries

**RAG Module (Standalone):**
- Located in `/rag_module/` - fully independent voice assistant context retrieval system
- FAISS-based vector store for sub-millisecond retrieval (~15ms measured, target <1ms)
- Per-user data isolation with FAISS indexes and JSON metadata
- Token budget management (2150 token limit for LLM prompts)
- User profile building and speaking style analysis
- Session memory management (in-memory, max 6 messages)
- See RAG Module section below for details

**Migration management:**
- All changes via Alembic (in `/alembic/versions/`)
- 4 existing migrations: initial schema, meeting columns, OAuth update, recording fields
- Always use `alembic revision --autogenerate` for schema changes

## Key Workflows

### Adding a New API Endpoint

1. Create Pydantic schemas in `app/schemas/`
2. Add endpoint handler in `app/api/v1/endpoints/`
3. Implement business logic in `app/services/`
4. Register route in `app/api/v1/api.py`
5. Test at http://localhost:8000/docs (Swagger UI)

### Modifying Database Schema

1. Edit SQLAlchemy model in `app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. **Review the auto-generated migration** in `alembic/versions/`
4. Apply: `alembic upgrade head`
5. Update corresponding Pydantic schemas in `app/schemas/`

### Adding Frontend Features

1. Create/modify page in `app/` directory (Next.js App Router)
2. Add API calls in `lib/api/` if needed
3. Use TypeScript for type safety
4. Style with Tailwind CSS classes
5. Use `useAuth()` hook for authentication state

### Working with Recall.ai Service

The `app/services/recall_service.py` (65KB) is the most comprehensive service. Key functions:
- `create_bot()` - Deploy bot to meeting URL
- `get_bot_status()` - Monitor bot state
- `get_transcript()` - Retrieve meeting transcript
- `handle_webhook()` - Process Recall.ai events
- `download_recording()` - Fetch video file

Always check bot status before operations.

### AI Summarization Pipeline

1. Transcript retrieved from Recall.ai via `recall_service.py`
2. Text preprocessing in `summarization.py`
3. Fine-tuned FLAN-T5 model inference (loaded from `best_model/`)
4. Extract summary and action items
5. Store in `meetings` table (`summary`, `action_items` columns)

Model weights are in `best_model/` directory (not tracked in git).

### Setting Up Real-Time Transcription

**Prerequisites:**
1. Redis must be installed and running (see [REDIS_SETUP_WINDOWS.md](REDIS_SETUP_WINDOWS.md))
2. Environment variables configured: `REDIS_URL`, `REALTIME_WEBHOOK_URL`, `WEBSOCKET_ALLOWED_ORIGINS`

**Backend:**
1. Redis pub/sub service initializes on startup ([app/main.py](app/main.py))
2. WebSocket endpoint registered at `/api/v1/realtime/ws/transcript/{meeting_id}`
3. Webhook endpoint at `/api/v1/realtime/webhook/recall` receives Recall.ai events
4. Events are published to Redis channel `meeting:{meeting_id}:transcript`

**Frontend:**
1. Import `RealtimeTranscript` component from [app/components/RealtimeTranscript.tsx](app/components/RealtimeTranscript.tsx)
2. Pass `meetingId` and `token` props
3. Component automatically connects to WebSocket and displays live updates
4. Features: auto-scroll, speaker grouping, copy/download, reconnect

**Testing:**
```bash
# Check Redis connection
redis-cli ping

# Test publish (backend running)
POST /api/v1/realtime/test/publish/{meeting_id}?text=Test

# Check WebSocket status
GET /api/v1/realtime/status/{meeting_id}
```

See [REALTIME_TRANSCRIPTION.md](REALTIME_TRANSCRIPTION.md) for complete setup guide.

### Voice Cloning and TTS (Text-to-Speech)

**Technology**: NeuTTS Nano with Q4 GGUF quantization for CPU inference

**Architecture**: Voice profile → Redis cache → Celery async jobs → Synthesized speech

**Prerequisites:**
1. eSpeak NG installed (phonemization - see [SETUP_TTS.md](SETUP_TTS.md))
2. NeuTTS installed: `git clone https://github.com/neuphonic/neutts.git && pip install -e ./neutts`
3. Redis running (for caching)
4. Celery worker running (for async synthesis)

**Workflow:**
1. User records 15-second voice sample on profile page
2. NeuTTS encodes voice → saves to `data/voice_profiles/{user_id}/`
3. User generates preview with custom text
4. System checks Redis cache first (instant if cached)
5. If not cached → Celery async job synthesizes speech
6. Frontend polls for completion → auto-plays when ready

**Performance Optimizations:**
- **Model pre-warming on startup** - Eliminates 30s first-request delay
- **Redis caching** - <50ms response for repeated phrases (40-60x faster)
- **Celery async jobs** - Non-blocking UI, instant API response
- **50-word limit** - Optimal synthesis time (2-3s max)
- **Job polling** - Real-time progress tracking

**Expected Latency:**
- First request (after pre-warm): 2-3 seconds
- Cached phrases: <50ms (instant)
- Average with 40% cache hit rate: ~1.2 seconds

**Key Files:**
- Backend: [app/services/tts_service.py](app/services/tts_service.py), [app/services/tts_cache.py](app/services/tts_cache.py), [app/services/tts_tasks.py](app/services/tts_tasks.py)
- API: [app/api/v1/endpoints/tts.py](app/api/v1/endpoints/tts.py)
- Frontend: [app/components/VoiceSetup.tsx](app/components/VoiceSetup.tsx), [lib/api/tts.ts](lib/api/tts.ts)

**Endpoints:**
- `POST /api/v1/tts/upload-voice` - Upload voice sample
- `GET /api/v1/tts/voice-status` - Check if user has voice profile
- `GET /api/v1/tts/voice-info` - Get profile info + cache stats
- `GET /api/v1/tts/original-recording` - Download original voice sample
- `POST /api/v1/tts/synthesize` - Sync synthesis (with cache)
- `POST /api/v1/tts/synthesize-async` - Async synthesis (returns job_id)
- `GET /api/v1/tts/job/{job_id}` - Poll job status
- `DELETE /api/v1/tts/voice` - Delete voice profile

**Celery Worker (Windows):**
```bash
celery -A app.core.celery worker --loglevel=info --pool=solo
```

**Why `--pool=solo` on Windows:**
- Windows has multiprocessing issues with default `prefork` pool
- `solo` pool = single-threaded, stable, no permission errors
- Still non-blocking for users (main benefit preserved)
- For production on Linux, use `prefork` or `gevent`

**Testing:**
```bash
# Upload voice
POST /api/v1/tts/upload-voice
  - audio_file: voice_sample.wav
  - ref_text: "My name is John..."

# Generate preview (async)
POST /api/v1/tts/synthesize-async
  - text: "Hello everyone"
  → Returns: {"job_id": "abc123", "status": "queued"}

# Poll for result
GET /api/v1/tts/job/abc123
  → Returns: {"status": "success", "result": {"audio_data": "base64..."}}

# Generate again (cache hit)
POST /api/v1/tts/synthesize-async
  - text: "Hello everyone"
  → Returns instant (<50ms)
```

See [SETUP_TTS.md](SETUP_TTS.md) and [TTS_LATENCY_OPTIMIZATIONS.md](TTS_LATENCY_OPTIMIZATIONS.md) for complete documentation.

## Configuration

All config via environment variables (`.env` file):

**Critical variables:**
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/digitaltwin
POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB

# Security
SECRET_KEY                        # JWT signing key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth (required)
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Recall.ai (required)
RECALL_API_KEY
RECALL_BASE_URL=https://us-east-1.recall.ai/api/v1

# Redis (required for real-time features)
REDIS_URL=redis://localhost:6379

# Real-Time Transcription
REALTIME_WEBHOOK_URL=http://localhost:8000/api/v1/realtime/webhook/recall
WEBSOCKET_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# Auto-join settings
AUTO_JOIN_ADVANCE_MINUTES=5       # How early to join
AUTO_JOIN_CHECK_INTERVAL=60       # Check frequency (seconds)

# AI model
VECTOR_DB_PATH, CHUNK_SIZE, CHUNK_OVERLAP  # For future RAG
```

Configuration is loaded via Pydantic `Settings` class in `app/core/config.py`.

## Important Technical Details

### Authentication Flow

1. User clicks login � `GET /api/v1/auth/google/login` returns OAuth URL
2. Google redirects to � `GET /api/v1/auth/google/callback`
3. Backend exchanges code for Google tokens, stores in DB (encrypted JSON)
4. Backend generates JWT access token, returns to frontend
5. Frontend stores JWT in localStorage as `auth_token` (consistent naming)
6. Frontend includes token in `Authorization: Bearer <token>` header
7. `GET /api/v1/auth/me` validates JWT and returns user info

**No password authentication** - OAuth only.

**Important notes:**
- Token key is `auth_token` (not `access_token`) - used consistently across the app
- Landing page validates tokens before redirecting to dashboard
- Invalid tokens are cleared silently without console errors
- Auth errors marked with `isAuthError` flag to suppress expected error logs

### Meeting Lifecycle

```
scheduled � bot_joining � in_progress � processing � completed
                �              �              �
           (Recall.ai)   (Recording)  (Summarization)
```

Status tracked in `meetings.status` column.

### Real-Time Transcription Flow

**Architecture:** Recall.ai → Backend Webhook → Redis Pub/Sub → WebSocket → Frontend

**Latency:** ~600ms end-to-end (speech to display)

**Flow:**
1. Bot joins meeting with `realtime_transcription` enabled (automatic)
2. Recall.ai sends `transcript.data` events to webhook endpoint
3. Webhook handler (`realtime.py`) processes events (<10ms)
4. Events published to Redis channel `meeting:{meeting_id}:transcript`
5. WebSocket manager subscribes to Redis and forwards to connected clients
6. Frontend `useRealtimeTranscript` hook receives and displays live updates

**Key files:**
- Backend: [app/api/v1/endpoints/realtime.py](app/api/v1/endpoints/realtime.py), [app/services/redis_pubsub.py](app/services/redis_pubsub.py), [app/services/websocket_manager.py](app/services/websocket_manager.py)
- Frontend: [lib/hooks/useRealtimeTranscript.ts](lib/hooks/useRealtimeTranscript.ts), [app/components/RealtimeTranscript.tsx](app/components/RealtimeTranscript.tsx)
- Schemas: [app/schemas/realtime.py](app/schemas/realtime.py)

**WebSocket URL:** `ws://localhost:8000/api/v1/realtime/ws/transcript/{meeting_id}?token={jwt}`

**Redis requirements:** Must be running on localhost:6379 (see [REDIS_SETUP_WINDOWS.md](REDIS_SETUP_WINDOWS.md) for Windows setup)

### Background Task Processing

Celery handles async operations:
- Auto-join scheduler checks calendar events
- Transcript processing after meeting ends
- AI summarization (can take minutes for large meetings)
- Calendar synchronization

**Must run Celery worker** for background tasks to execute.

### Frontend-Backend Integration

- Frontend uses `lib/api/client.ts` HTTP client
- JWT token stored in React state and localStorage
- Auth context provider in `app/contexts/`
- Protected routes check auth status via `useAuth()` hook
- API base URL: `http://localhost:8000/api/v1`

## Common Patterns

### Database Queries

```python
# Always use async with SQLAlchemy
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_user_meetings(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Meeting).filter(Meeting.user_id == user_id)
    )
    return result.scalars().all()
```

### Error Handling

```python
# Use FastAPI HTTPException
from fastapi import HTTPException, status

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Meeting not found"
)
```

### Service Dependencies

```python
# Dependency injection pattern
from fastapi import Depends
from app.core.database import get_db
from app.services.auth import get_current_user

@router.get("/meetings/")
async def list_meetings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Implementation
```

## Documentation Files

**Core Documentation:**
- `README.md` (674 lines) - Main project overview
- `DATABASE_SCHEMA.md` (462 lines) - Complete schema documentation
- `OAUTH_SETUP.md` (187 lines) - OAuth configuration guide
- `PROJECT_STRUCTURE.md` - File structure details
- `INSTALL_GUIDE.md` - Installation instructions
- `LOCAL_SETUP.md` - Local development setup

**Feature-Specific Guides:**
- `REALTIME_TRANSCRIPTION.md` (656 lines) - **Complete real-time WebSocket setup guide**
- `REDIS_SETUP_WINDOWS.md` (298 lines) - Redis installation and configuration for Windows
- `TRANSCRIPT_ENDPOINTS.md` - Transcript API docs
- `QUICKSTART_REALTIME.md` - Quick start guide for real-time features
- `AUTH_FIXES.md` - Authentication flow improvements and fixes
- `FIXES_APPLIED.md` - Backend startup fixes

API docs auto-generated at http://localhost:8000/docs (Swagger UI).

## Git Workflow

**Current status:**
- Main branch: `main`
- Feature branch: `feature/response_LLM` (currently active)
- Recent additions: TTS voice cloning, RAG/LLM integration, prompt engineering optimizations
- Modified files: Backend API endpoints, frontend components, RAG module, configuration files
- Untracked: `rag_module/models/`, `rag_module/data/`, `data/voice_profiles/`, test files, neutts/

**Recent features added:**
- **TTS voice cloning** with NeuTTS Nano, Redis caching, Celery async jobs
- **RAG/LLM integration** with Qwen2.5-0.5B model, FAISS retrieval, Redis caching
- **Prompt engineering** optimizations for small LLM (400% accuracy improvement)
- **Automatic transcript storage** in RAG when meetings complete
- **Frontend AI Assistant** interface at `/dashboard/rag`
- Real-time transcription via WebSocket (previous feature)
- Redis pub/sub integration for live updates (previous feature)

**When committing:**
- Keep feature work in feature branches
- Use descriptive commit messages
- Don't commit `.env` files or model weights
- Don't commit large documentation files unless necessary for reference
- Run `npm run lint` before committing frontend changes

## Testing

**Backend testing:**
- Test scripts in root: `test_summarization.py`, `test_calendar_webhook.py`
- Interactive API testing: http://localhost:8000/docs
- Real-time transcription test: `POST /api/v1/realtime/test/publish/{meeting_id}`

**Frontend testing:**
- ESLint: `npm run lint`
- Build test: `npm run build` (catches TypeScript errors)
- Real-time features: Use browser DevTools to monitor WebSocket connections

No formal test suite currently implemented.

## Common Issues and Troubleshooting

### Redis Connection Failed

**Symptom:** Backend logs show "Redis pub/sub initialization failed"

**Solutions:**
1. Check Redis is running: `redis-cli ping` (Windows: use full path or add to PATH)
2. Verify `REDIS_URL` in `.env`: `redis://localhost:6379`
3. Windows: See [REDIS_SETUP_WINDOWS.md](REDIS_SETUP_WINDOWS.md) for setup instructions

### Authentication "Could not validate credentials"

**Symptom:** Console error on landing page, redirect loop

**Solutions:**
1. Clear localStorage: `localStorage.clear()`
2. Check token key is `auth_token` (not `access_token`)
3. Verify landing page validates tokens before redirecting
4. See [AUTH_FIXES.md](AUTH_FIXES.md) for details

### WebSocket Connection Closed

**Symptom:** Real-time transcript not updating, WebSocket disconnects

**Solutions:**
1. Verify JWT token is passed: `?token={jwt}`
2. Check token hasn't expired: `GET /api/v1/auth/me`
3. Ensure Redis is running and connected
4. Check CORS: `WEBSOCKET_ALLOWED_ORIGINS` includes frontend URL

### No Transcript Chunks Received

**Symptom:** WebSocket connects but no messages appear

**Solutions:**
1. Check bot status: `GET /api/v1/meetings/bot/{bot_id}/status`
2. Verify webhook URL is accessible: `REALTIME_WEBHOOK_URL`
3. Test manual publish: `POST /api/v1/realtime/test/publish/{meeting_id}`
4. Check Recall.ai dashboard for webhook delivery logs

### Backend Won't Start

**Symptom:** Import errors, module not found

**Solutions:**
1. Activate virtual environment: `venv\Scripts\activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Check database connection: `DATABASE_URL` in `.env`
4. Run migrations: `alembic upgrade head`
5. See [FIXES_APPLIED.md](FIXES_APPLIED.md) for startup fixes

## RAG Module - Voice Assistant Context Retrieval

### Overview

The RAG (Retrieval Augmented Generation) module is a **standalone system** for ultra-low-latency context retrieval in voice assistant applications. It's located in `/rag_module/` and operates independently from the main DigitalTwin application.

**Key characteristics:**
- **FAISS-based vector store** - Sub-millisecond retrieval target (~0.3ms theoretical, ~15ms measured with overhead)
- **CPU-only operation** - No GPU dependencies
- **Per-user isolation** - Each user has separate FAISS index and metadata files
- **Token budget enforcement** - Strict 2150 token limit for LLM prompts
- **Offline-capable** - Falls back to word-based token estimation when tiktoken unavailable
- **User profiling** - Automatic speaking style analysis and personalization

### Architecture

```
Voice Assistant Pipeline:
User Voice → Speech-to-Text → [RAG Module] → LLM → Text-to-Speech → Audio Output
                                     ↓
                            Context Retrieval (~15ms)
                                     ↓
                              ┌──────────────────┐
                              │  RAG Pipeline    │
                              ├──────────────────┤
                              │  1. Embedder     │ ← all-MiniLM-L6-v2 (384-dim)
                              │  2. Retriever    │ ← FAISS IndexFlatL2
                              │  3. Profile Mgr  │ ← User style analysis
                              │  4. Session Mem  │ ← Last 6 messages
                              │  5. Prompt Build │ ← Token budget (2150)
                              └──────────────────┘
                                     ↓
                          Per-User Data Storage:
                          data/users/{user_id}/
                            ├── faiss_index.bin
                            ├── metadata.json
                            └── profile.json
```

### Module Structure

```
rag_module/
├── rag/                          # Core RAG implementation
│   ├── __init__.py              # Module exports
│   ├── embedder.py              # Text-to-vector conversion (all-MiniLM-L6-v2)
│   ├── faiss_store.py           # FAISS vector store with persistence
│   ├── retriever.py             # Similarity search and ranking
│   ├── memory_manager.py        # Session memory (in-memory, max 6 msgs)
│   ├── profile_manager.py       # User profiling and style analysis
│   ├── prompt_builder.py        # Token budget and prompt assembly
│   ├── llm_generator.py         # **LLM inference** (Qwen2.5-0.5B, llama-cpp)
│   ├── llm_cache.py             # **Redis caching** for LLM responses
│   └── pipeline.py              # Main RAG orchestrator
├── tests/                        # Comprehensive test suite
│   ├── __init__.py
│   ├── test_faiss_store.py      # Vector store tests
│   ├── test_retriever.py        # Retrieval tests
│   ├── test_profile.py          # Profile manager tests
│   └── test_pipeline.py         # End-to-end integration tests
├── models/                       # **LLM model files**
│   ├── qwen2.5-0.5b-instruct-q4_k_m.gguf  # Quen model (not in git)
│   └── README.md                # Model download instructions
├── data/                         # User data storage
│   └── users/                   # Per-user directories
│       └── {user_id}/
│           ├── faiss_index.bin  # FAISS vector index
│           ├── metadata.json    # Exchange metadata
│           └── profile.json     # User profile
├── config.py                     # **Configuration** (model settings, cache, etc.)
├── demo.py                       # Full system demonstration
├── benchmark.py                  # Latency benchmarking tool
├── LLM_INTEGRATION.md            # **LLM integration guide**
├── QUICKSTART_LLM.md             # **Quick start for LLM features**
└── test_simple.py               # Quick sanity check
```

### Key Components

**1. EmbeddingEngine (`embedder.py`)**
- Model: `all-MiniLM-L6-v2` (384-dimensional embeddings)
- CPU-optimized sentence-transformers
- L2 normalization for cosine similarity compatibility
- ~10ms embedding latency per query

**2. FAISSStore (`faiss_store.py`)**
- FAISS `IndexFlatL2` for exact nearest neighbor search
- Per-user index files with automatic persistence
- Immediate write-through on every add operation
- Returns results sorted by similarity score (0-1 range)

**3. ContextRetriever (`retriever.py`)**
- Caches FAISSStore instances per user
- Threshold-based filtering (default: 0.5 similarity)
- Formatted context output for LLM consumption
- Retrieval latency tracking for monitoring

**4. UserProfileManager (`profile_manager.py`)**
- Automatic speaking style analysis:
  - Formality level (casual/formal)
  - Average message length (short/medium/long)
  - Technical term usage detection
  - Common vocabulary extraction
  - Topic identification
- Concise style summaries (<200 words) for prompt inclusion

**5. SessionMemory (`memory_manager.py`)**
- In-memory message storage (Python list)
- Maximum 6 messages (configurable)
- Formatted output for prompt assembly
- Automatic overflow handling (FIFO)

**6. PromptBuilder (`prompt_builder.py`)**
- Token budget allocation (2150 total):
  - System prompt: 300 tokens
  - Profile summary: 150 tokens
  - Retrieved context: 600 tokens
  - Session history: 400 tokens
  - User message: 200 tokens
  - Response buffer: 500 tokens
- Intelligent trimming (context first, then history)
- Offline fallback (word-based estimation when tiktoken unavailable)
- Accurate token counting with tiktoken (cl100k_base encoding)

**7. LLMGenerator (`llm_generator.py`)**
- Qwen2.5-0.5B-Instruct model loading and inference
- llama-cpp-python backend for CPU execution
- Streaming and non-streaming generation modes
- Configurable temperature, top-p, top-k sampling
- Stop sequences to prevent rambling
- Model pre-warming on startup (eliminates 10-15s delay)

**8. LLMResponseCache (`llm_cache.py`)**
- Redis-based response caching with SHA256 keys
- 24-hour TTL (configurable)
- Cache hit/miss tracking
- <50ms response time for cached queries
- Automatic cache key generation from prompt + params

**9. RAGPipeline (`pipeline.py`)**
- Main orchestrator class
- User initialization and lifecycle management
- Message processing and exchange storage
- Session management (start/end)
- User statistics and analytics
- **LLM integration** - Calls LLMGenerator for response generation

### Usage Example

```python
from rag.pipeline import RAGPipeline

# Initialize pipeline
pipeline = RAGPipeline(base_path="data/users")

# Initialize new user
user_info = pipeline.initialize_user("user123")
# Returns: {is_new_user: True, total_past_exchanges: 0, profile: {...}}

# Process user message
result = pipeline.process_message("user123", "How do I fix this error?")
# Returns: {
#   prompt: "...",                    # Assembled LLM prompt
#   retrieved_context: "...",         # Relevant past exchanges
#   token_breakdown: {...},           # Token usage details
#   num_results_retrieved: 2,         # Number of context items
#   retrieval_latency_ms: 12.5        # Retrieval performance
# }

# Store exchange after LLM response
pipeline.store_exchange("user123",
    user_message="How do I fix this error?",
    assistant_response="Check the logs for details."
)

# End session (clears session memory, keeps long-term storage)
stats = pipeline.end_session("user123")
# Returns: {session_cleared: True, messages_in_session: 5, total_exchanges_stored: 5}

# Get user statistics
stats = pipeline.get_user_stats("user123")
# Returns: {user_id, total_exchanges, session_messages, profile: {...}}
```

### Running Tests

```bash
cd rag_module

# Individual test suites
python tests/test_faiss_store.py   # Vector store tests
python tests/test_retriever.py     # Retrieval tests
python tests/test_profile.py       # Profile manager tests
python tests/test_pipeline.py      # Integration tests

# Demo (simulates 2 conversation sessions)
python demo.py

# Benchmark (50 exchanges, 100 queries)
python benchmark.py
```

### Performance Metrics

**Measured latency (test_pipeline.py):**
- Average retrieval: ~15ms (includes embedding generation)
- Pure FAISS search: ~0.3ms (theoretical)
- Overhead breakdown:
  - Embedding generation: ~10ms (sentence-transformers)
  - FAISS search: ~0.3ms
  - Result formatting: ~2ms
  - Metadata lookup: ~2ms

**Token budget compliance:**
- All test cases within 2150 token limit
- Automatic trimming when needed
- Average prompt size: 150-300 tokens

**Storage efficiency:**
- FAISS index: ~50KB per 100 exchanges
- Metadata JSON: ~20KB per 100 exchanges
- Profile JSON: ~2KB per user

### Configuration

No environment variables needed - fully standalone. Configuration is code-based:

```python
# In prompt_builder.py
self.budget = {
    "system_prompt": 300,
    "profile_summary": 150,
    "retrieved_context": 600,
    "session_history": 400,
    "user_message": 200,
    "response_buffer": 500,
    "total_limit": 2150
}

# In retriever.py
def retrieve(self, user_id: str, query: str,
             top_k: int = 3, threshold: float = 0.5):
    # threshold: minimum similarity score (0.0-1.0)
    # top_k: maximum results to return
```

### Integration with Main App - COMPLETED

The RAG module is **now fully integrated** with the main DigitalTwin FastAPI application.

#### LLM Integration (Qwen2.5-0.5B-Instruct)

**Model Details:**
- Model: Qwen2.5-0.5B-Instruct (Q4_K_M quantization, ~400MB)
- Backend: llama-cpp-python for CPU inference
- Context window: 2150 tokens (prompt) + 1000 tokens (response)
- Caching: Redis with 24-hour TTL (SHA256-based keys)
- Performance: 2-6s generation, <50ms cached

**Architecture:**
```
User Query → RAG Service → FAISS Retrieval → Prompt Assembly → Qwen LLM → Redis Cache → Response
                ↓                                                    ↓
          Per-user FAISS                                    llama-cpp-python
```

**Key Files:**
- `rag_module/rag/llm_generator.py` - LLM inference with llama-cpp
- `rag_module/rag/llm_cache.py` - Redis caching layer
- `rag_module/config.py` - Model configuration (max_tokens, temperature, etc.)
- `app/services/rag_service.py` - FastAPI integration wrapper
- `app/api/v1/endpoints/rag.py` - REST API endpoints

**Endpoints:**
- `POST /api/v1/rag/query` - Query with context retrieval + LLM generation
- `GET /api/v1/rag/stats` - User statistics (total exchanges, profile)
- `GET /api/v1/rag/cache/stats` - Cache hit/miss rates
- `POST /api/v1/rag/store-transcript/{meeting_id}` - Manual transcript storage
- `DELETE /api/v1/rag/session` - Clear session memory

**Automatic Transcript Storage:**
When a meeting status changes to "completed", the system automatically:
1. Fetches full transcript from Recall.ai
2. Groups consecutive speaker messages
3. Stores each speaker's dialogue as separate exchange
4. Format: `"{speaker}: {text}"` → stored in user's FAISS index

**Prompt Engineering for Small LLMs:**
The system uses optimized prompting for the 0.5B model:

```
System Prompt (simplified, direct instructions):
  "You are a helpful assistant. Answer questions directly using the provided context.

  INSTRUCTIONS:
  1. Use ONLY information from 'Past conversations' section if provided
  2. Give direct, specific answers (avoid vague responses)
  3. If the context contains the answer, extract it clearly
  4. If no relevant context, say 'I don't have information about that'
  5. Keep answers concise (2-3 sentences)"

Context Section:
  ---
  Past conversations:
  [Retrieved context from FAISS]
  ---

Question/Answer Format:
  Question: {user_query}
  Answer:
```

**Performance Optimizations Applied:**
- Retrieval threshold lowered from 0.5 to 0.0 (accept all results, use top_k=3)
- Response buffer increased from 500 to 1000 tokens
- Default max_tokens increased from 200 to 500
- Removed style summary (confusing for small models)
- Removed session history (reduces noise)
- Clear question/answer separation

**Results:**
- Retrieval accuracy: 83% (5/6 test queries)
- LLM response accuracy: 83% (5/6 test queries) - **400% improvement** from 17%
- Average response length: 25-150 tokens (was 3-15)
- Total latency: 2-6 seconds uncached, <50ms cached

**Frontend Integration:**
- Component: `frontend/web_gui/app/components/RagQuery.tsx`
- Page: `/dashboard/rag` (AI Assistant)
- Features: Query interface, latency metrics, sample queries, cache stats, user stats
- API client: `frontend/web_gui/lib/api/rag.ts`

**Configuration (rag_module/config.py):**
```python
MODEL_PATH = "models/qwen2.5-0.5b-instruct-q4_k_m.gguf"
MODEL_MAX_OUTPUT_TOKENS = 500  # Increased for better quality
MODEL_TEMPERATURE = 0.7
MODEL_TOP_P = 0.9
MODEL_TOP_K = 40
CACHE_TTL_SECONDS = 86400  # 24 hours
```

**Testing:**
```bash
# Test query (via frontend or API)
POST /api/v1/rag/query
{
  "message": "What database did we decide to use?",
  "use_cache": true,
  "auto_store": false,
  "max_tokens": 500
}

# Returns:
{
  "response": "We decided to use PostgreSQL with SQLAlchemy ORM...",
  "retrieval_latency_ms": 45.2,
  "llm_latency_ms": 3421.5,
  "total_latency_ms": 3466.7,
  "tokens_generated": 67,
  "cached": false,
  "context_items": 3
}
```

**Documentation:**
- `rag_module/LLM_INTEGRATION.md` - Complete LLM integration guide
- `rag_module/QUICKSTART_LLM.md` - Quick start for LLM features

### Known Issues

**1. Retrieval Latency Higher Than Target**
- Target: <1ms
- Measured: ~15ms average
- Cause: Embedding generation overhead (~10ms)
- Solution: Pre-compute and cache common query embeddings, or use faster embedding model

**2. Offline Tiktoken Fallback**
- tiktoken requires internet to download encoding first time
- Falls back to word-based estimation (less accurate)
- Download cl100k_base.tiktoken manually if offline environment:
  ```bash
  # Download once with internet connection
  python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
  ```

**3. Windows Unicode Errors**
- Unicode checkmarks (✓) cause `UnicodeEncodeError` in Windows console
- Fixed: All checkmarks replaced with `[OK]` throughout codebase
- Pattern: `✓` → `[OK]`

### Future Enhancements

**Performance optimizations:**
- [ ] Switch to faster embedding model (e.g., BGE-small, 100ms → 5ms)
- [ ] Implement embedding cache for common queries
- [ ] Use FAISS IVF index for larger datasets (>10k exchanges)
- [ ] Batch processing for multiple queries

**Feature additions:**
- [ ] Multi-modal support (images, documents)
- [ ] Hybrid search (keyword + semantic)
- [ ] Reranking with cross-encoder
- [ ] Automatic exchange importance scoring
- [ ] Export/import user data
- [ ] Multi-language support

**Integration work:**
- [ ] REST API endpoints in main FastAPI app
- [ ] Database storage option (PostgreSQL vector extension)
- [ ] Redis caching layer
- [ ] Metrics and monitoring dashboard

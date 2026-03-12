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
celery -A app.core.celery worker --loglevel=info  # Required for async tasks

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

**Service Layer (`app/services/`):**
- `recall_service.py` (65KB) - **Most critical service** - Recall.ai bot management, recording, transcription, webhook handling
- `redis_pubsub.py` - Redis pub/sub message broker for real-time features
- `websocket_manager.py` - WebSocket connection manager for per-meeting transcript streams
- `summarization.py` - FLAN-T5 model inference, action item extraction
- `auth.py` - OAuth flow, JWT generation, token refresh
- `calendar.py` - Google Calendar integration
- `meeting.py` - Meeting business logic
- `meeting_automation.py` - Auto-join scheduling logic

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
- `app/contexts/` - React context providers (theme, auth)
- `app/styles/` - CSS modules and Tailwind utilities

## Database Schema

**Core tables (implemented):**
1. **users** - OAuth tokens, profile, `bot_name` (custom name for meeting bot), `enable_backend_tasks`
2. **meetings** - Full lifecycle tracking, `transcript` (text), `summary` (text), `action_items` (JSON array)
3. **bots** - Recall.ai bot status, `recording_url`, `video_url`, `meeting_id` FK
4. **calendar_events** - Google Calendar sync, meeting URL extraction
5. **emails** - Email processing data

**Planned tables (RAG system):**
- documents, document_chunks, embeddings, rag_queries

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
- Feature branch: `feature/realtimetransc` (currently active)
- Recent additions: Real-time transcription, Redis pub/sub, WebSocket manager, auth fixes
- Modified files: Backend API endpoints, frontend components, configuration files
- Untracked: `best_model/`, documentation files, Redis helper scripts

**Recent features added:**
- Real-time transcription via WebSocket (656-line documentation)
- Redis pub/sub integration for live updates
- Authentication flow fixes (token validation, error handling)
- Frontend real-time transcript component

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

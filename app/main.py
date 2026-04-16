"""
Digital Twin Main Application
AI-powered meeting automation system with Google OAuth
"""

# Fix Unicode encoding issues on Windows
import sys
import os
if os.name == 'nt':  # Windows
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.api import api_router
from app.services.webhook_auto_setup import webhook_auto_setup
from app.services.redis_pubsub import init_redis_pubsub, shutdown_redis_pubsub
from app.services.websocket_manager import get_websocket_manager
from app.services.meeting_status_monitor import start_meeting_status_monitor, stop_meeting_status_monitor
from app.services.filler_audio_injector import filler_audio_injector


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== STARTUP =====
    print("🚀 Starting DigitalTwin application...", flush=True)

    # Initialize database
    await init_db()
    print("✅ Database initialized", flush=True)

    # Initialize Redis pub/sub for real-time transcription
    try:
        await init_redis_pubsub()
        print("✅ Redis pub/sub service initialized", flush=True)
    except Exception as e:
        print(f"⚠️ Redis pub/sub initialization failed: {e}", flush=True)
        print("   Real-time transcription will be unavailable", flush=True)

    # Auto-setup webhook environment for demo (optional)
    # This will try to setup ngrok automatically if needed
    try:
        setup_result = await webhook_auto_setup.auto_setup_for_demo()
        if setup_result["status"] == "ready":
            print(f"🚀 Demo environment ready! Webhook URL: {setup_result['webhook_url']}", flush=True)
            print("📍 Use /api/v1/calendar/demo-setup endpoint for one-click demo setup", flush=True)
        elif setup_result["status"] == "manual_setup_required":
            print("⚠️ Manual webhook setup required (ngrok not available)", flush=True)
            print("📍 Use /api/v1/calendar/setup-webhook endpoint for manual setup", flush=True)
    except Exception as e:
        print(f"⚠️ Auto-setup failed: {e}", flush=True)
        print("📍 Use /api/v1/calendar/setup-webhook endpoint for manual setup", flush=True)

    # Start meeting status monitor (polls Recall.ai for bot status updates)
    try:
        poll_interval = int(os.getenv("MEETING_STATUS_POLL_INTERVAL", "30"))
        await start_meeting_status_monitor(poll_interval=poll_interval)
        print(f"✅ Meeting status monitor started (checking every {poll_interval}s)", flush=True)
    except Exception as e:
        print(f"⚠️ Meeting status monitor failed to start: {e}", flush=True)
        print("   Meeting statuses will need to be updated manually", flush=True)

    # Pre-warm TTS model (eliminates 30s first-request delay)
    try:
        print("🔥 Pre-warming TTS model...", flush=True)
        from app.services.tts_service import tts_service
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, tts_service._load_model)
        print("✅ TTS model pre-warmed and ready (eliminates first-request delay)", flush=True)
    except Exception as e:
        print(f"⚠️ TTS model pre-warming failed: {e}", flush=True)
        print("   First TTS request will be slower (~30s)", flush=True)

    # Pre-warm RAG/LLM model (eliminates 10-15s first-request delay)
    try:
        print("🔥 Pre-warming RAG/LLM model (this may take 90-120s on first load)...", flush=True)
        from app.services.rag_service import rag_service
        import asyncio

        # Use timeout to prevent hanging during startup (3 minutes max)
        try:
            await asyncio.wait_for(
                rag_service.initialize(),
                timeout=180.0  # 3 minutes timeout
            )
            print("✅ RAG/LLM model pre-warmed and ready (eliminates first-request delay)", flush=True)
        except asyncio.TimeoutError:
            print("⚠️ RAG/LLM model pre-warming timed out after 3 minutes", flush=True)
            print("   RAG features may not be available", flush=True)
    except Exception as e:
        print(f"⚠️ RAG/LLM model pre-warming failed: {e}", flush=True)
        print("   First RAG query will be slower (~10-15s)", flush=True)

    # Preload context-aware filler audio for instant injection (NEW)
    try:
        print("🔥 Preloading context-aware filler audio...", flush=True)
        loaded_count = filler_audio_injector.preload_all_fillers()
        print(f"✅ Filler audio preloaded: {loaded_count} clips (instant 0-50ms injection ready)", flush=True)
    except Exception as e:
        print(f"⚠️ Filler audio preload failed (non-critical): {e}", flush=True)
        print("   Filler injection may be slower on first use", flush=True)

    print("✅ DigitalTwin application started successfully!", flush=True)
    print(f"📡 Real-time transcription webhook: {settings.REALTIME_WEBHOOK_URL}", flush=True)
    print(f"🔌 WebSocket endpoint: ws://localhost:8000/api/v1/realtime/ws/transcript/{{meeting_id}}", flush=True)

    yield

    # ===== SHUTDOWN =====
    print("🛑 Shutting down DigitalTwin application...", flush=True)

    # Stop meeting status monitor
    try:
        await stop_meeting_status_monitor()
        print("✅ Meeting status monitor stopped", flush=True)
    except Exception as e:
        print(f"⚠️ Error stopping meeting status monitor: {e}", flush=True)

    # Cleanup WebSocket connections
    ws_manager = get_websocket_manager()
    await ws_manager.cleanup_all_connections()
    print("✅ WebSocket connections closed", flush=True)

    # Shutdown Redis pub/sub
    await shutdown_redis_pubsub()
    print("✅ Redis pub/sub service shut down", flush=True)

    # Cleanup webhooks
    webhook_auto_setup.cleanup()
    print("✅ Application shutdown complete", flush=True)


app = FastAPI(
    title="Digital Twin",
    description="AI Digital Twin for Meeting Automation with Google OAuth",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "auth",
            "description": "Authentication operations with Google OAuth",
        },
        {
            "name": "users",
            "description": "User management operations",
        }
    ]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Digital Twin API is running", 
        "version": "1.0.0",
        "auth": "Google OAuth enabled",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "digital_twin_profile": "/digital-twin-profile"
    }


@app.get("/digital-twin-profile")
async def serve_digital_twin_profile():
    """Serve the digital twin profile management page"""
    return FileResponse("static/digital_twin_profile.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "auth": "Google OAuth ready"}


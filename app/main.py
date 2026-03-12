"""
Digital Twin Main Application
AI-powered meeting automation system with Google OAuth
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.api import api_router
from app.services.webhook_auto_setup import webhook_auto_setup
from app.services.redis_pubsub import init_redis_pubsub, shutdown_redis_pubsub
from app.services.websocket_manager import get_websocket_manager
from app.services.meeting_status_monitor import start_meeting_status_monitor, stop_meeting_status_monitor


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== STARTUP =====
    print("🚀 Starting DigitalTwin application...")

    # Initialize database
    await init_db()
    print("✅ Database initialized")

    # Initialize Redis pub/sub for real-time transcription
    try:
        await init_redis_pubsub()
        print("✅ Redis pub/sub service initialized")
    except Exception as e:
        print(f"⚠️ Redis pub/sub initialization failed: {e}")
        print("   Real-time transcription will be unavailable")

    # Auto-setup webhook environment for demo (optional)
    # This will try to setup ngrok automatically if needed
    try:
        setup_result = await webhook_auto_setup.auto_setup_for_demo()
        if setup_result["status"] == "ready":
            print(f"🚀 Demo environment ready! Webhook URL: {setup_result['webhook_url']}")
            print("📍 Use /api/v1/calendar/demo-setup endpoint for one-click demo setup")
        elif setup_result["status"] == "manual_setup_required":
            print("⚠️ Manual webhook setup required (ngrok not available)")
            print("📍 Use /api/v1/calendar/setup-webhook endpoint for manual setup")
    except Exception as e:
        print(f"⚠️ Auto-setup failed: {e}")
        print("📍 Use /api/v1/calendar/setup-webhook endpoint for manual setup")

    # Start meeting status monitor (polls Recall.ai for bot status updates)
    try:
        poll_interval = int(os.getenv("MEETING_STATUS_POLL_INTERVAL", "30"))
        await start_meeting_status_monitor(poll_interval=poll_interval)
        print(f"✅ Meeting status monitor started (checking every {poll_interval}s)")
    except Exception as e:
        print(f"⚠️ Meeting status monitor failed to start: {e}")
        print("   Meeting statuses will need to be updated manually")

    print("✅ DigitalTwin application started successfully!")
    print(f"📡 Real-time transcription webhook: {settings.REALTIME_WEBHOOK_URL}")
    print(f"🔌 WebSocket endpoint: ws://localhost:8000/api/v1/realtime/ws/transcript/{{meeting_id}}")

    yield

    # ===== SHUTDOWN =====
    print("🛑 Shutting down DigitalTwin application...")

    # Stop meeting status monitor
    try:
        await stop_meeting_status_monitor()
        print("✅ Meeting status monitor stopped")
    except Exception as e:
        print(f"⚠️ Error stopping meeting status monitor: {e}")

    # Cleanup WebSocket connections
    ws_manager = get_websocket_manager()
    await ws_manager.cleanup_all_connections()
    print("✅ WebSocket connections closed")

    # Shutdown Redis pub/sub
    await shutdown_redis_pubsub()
    print("✅ Redis pub/sub service shut down")

    # Cleanup webhooks
    webhook_auto_setup.cleanup()
    print("✅ Application shutdown complete")


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
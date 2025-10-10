"""
Digital Twin Main Application
AI-powered meeting automation system with Google OAuth
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.api import api_router
from app.services.webhook_auto_setup import webhook_auto_setup


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    
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
    
    yield
    
    # Shutdown
    webhook_auto_setup.cleanup()


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


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Digital Twin API is running", 
        "version": "1.0.0",
        "auth": "Google OAuth enabled",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "auth": "Google OAuth ready"}
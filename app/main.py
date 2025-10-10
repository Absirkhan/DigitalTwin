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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


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

# Mount static files
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Serve login page"""
    static_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "login.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    return {"message": "Digital Twin API is running", "auth": "Google OAuth enabled"}


@app.get("/login")
async def login_page():
    """Serve login page"""
    static_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "login.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    return {"message": "Login page not found"}


@app.get("/auth/success")
async def auth_success():
    """Handle successful authentication redirect"""
    static_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "auth_success.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    return {"message": "Authentication successful"}


@app.get("/auth/error")
async def auth_error():
    """Handle authentication error redirect"""
    static_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "auth_error.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    return {"message": "Authentication failed"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "auth": "Google OAuth ready"}
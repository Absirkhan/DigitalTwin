"""
API v1 Router
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    meetings,
    calendar,
    summarization,
    realtime,
    tts,
    rag
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(meetings.router, prefix="/meetings", tags=["meetings"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(summarization.router, prefix="/summarization", tags=["summarization"])
api_router.include_router(realtime.router, prefix="/realtime", tags=["realtime"])
api_router.include_router(tts.router, prefix="/tts", tags=["text-to-speech"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
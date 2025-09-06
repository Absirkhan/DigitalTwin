"""
Recall API service for meeting bot integration
"""

import httpx
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
import os

from app.schemas.meeting import MeetingJoinRequest, MeetingJoinResponse
from app.core.config import settings


class MeetingStatus(str, Enum):
    JOINING = "joining"
    JOINED = "joined"
    RECORDING = "recording"
    LEFT = "left"
    ERROR = "error"


class MeetingInfo(BaseModel):
    meeting_id: str
    meeting_url: str
    platform: str
    status: MeetingStatus
    bot_id: Optional[str] = None
    created_at: datetime


class RecallService:
    def __init__(self):
        # Try to get API key from environment directly as fallback
        api_key = settings.RECALL_API_KEY or os.getenv('RECALL_API_KEY', '')
        base_url = settings.RECALL_BASE_URL or os.getenv('RECALL_BASE_URL', 'https://api.recall.ai/api/v1')
        
        self.base_url = base_url
        
        # Debug logging for API key
        print(f"DEBUG: RECALL_API_KEY from settings: {'***' + settings.RECALL_API_KEY[-4:] if settings.RECALL_API_KEY else 'None'}")
        print(f"DEBUG: RECALL_API_KEY from env: {'***' + os.getenv('RECALL_API_KEY', '')[-4:] if os.getenv('RECALL_API_KEY') else 'None'}")
        print(f"DEBUG: Final API key: {'***' + api_key[-4:] if api_key else 'None'}")
        print(f"DEBUG: RECALL_BASE_URL: {self.base_url}")
        print(f"DEBUG: Using Token authentication (not Bearer)")
        
        # Check if API key exists and is not empty
        if not api_key or api_key.strip() == "":
            print("WARNING: RECALL_API_KEY is empty or not set!")
            
        self.headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json"
        }
        
        print(f"DEBUG: Headers configured: Authorization=Token ***{api_key[-4:] if api_key else 'None'}")

    def _detect_meeting_platform(self, meeting_url: str) -> str:
        """Detect meeting platform from URL"""
        if "zoom.us" in meeting_url:
            return "zoom"
        elif "teams.microsoft.com" in meeting_url:
            return "teams"
        elif "meet.google.com" in meeting_url:
            return "google_meet"
        else:
            return "unknown"

    async def test_authentication(self):
        """Test authentication with the correct Token method"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test with the Token authentication method
                response = await client.get(
                    f"{self.base_url}/bot",
                    headers=self.headers
                )
                return {
                    "auth_type": "Token",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "response_preview": response.text[:200] if response.text else ""
                }
        except Exception as e:
            return {
                "auth_type": "Token",
                "error": str(e),
                "success": False
            }

    async def join_meeting(self, request: MeetingJoinRequest):
        """Join a meeting using the Recall API with enhanced transcript and audio configuration"""
        try:
            # Prepare the payload for Recall API according to official documentation
            payload = {
                "meeting_url": str(request.meeting_url),
                "recording_config": {
                    "transcript": {
                        "provider": {
                            "meeting_captions": {}
                        }
                    },
                    "audio_mixed_raw": {},
                },
                "automatic_leave": {
                    "silence_detection": {
                        "timeout": 3600,
                        "activate_after": 1200
                    },
                    "waiting_room_timeout": 60,
                    "noone_joined_timeout": 600,
                    "everyone_left_timeout": 2,
                    "in_call_not_recording_timeout": 1200
                }
            }

            # Add bot name if provided
            if request.bot_name:
                payload["bot_name"] = request.bot_name

            # Add real-time endpoints for live processing if needed
            if (hasattr(request, "enable_realtime_processing") 
                and request.enable_realtime_processing):
                payload["recording_config"]["realtime_endpoints"] = [
                    {
                        "type": "websocket",
                        "config": {
                            "url": f"{settings.RECALL_BASE_URL}/webhooks/realtime",
                            "events": [
                                "transcript.data",  # Real-time transcript events
                                "audio_mixed_raw.data",  # Real-time audio events
                            ],
                        },
                    }
                ]

            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            # Debug logging
            print(f"DEBUG: Making request to {self.base_url}/bot")
            print(f"DEBUG: Headers: {dict(self.headers)}")
            print(f"DEBUG: Payload keys: {list(payload.keys())}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/bot", 
                    headers=self.headers, 
                    json=payload
                )

                # Check if response is successful
                if response.status_code == 201:
                    try:
                        data = response.json()
                        meeting_info = MeetingInfo(
                            meeting_id=data.get("id", ""),
                            meeting_url=str(request.meeting_url),
                            platform=self._detect_meeting_platform(str(request.meeting_url)),
                            status=MeetingStatus.JOINING,
                            bot_id=data.get("id"),
                            created_at=datetime.utcnow(),
                        )

                        # Return a proper MeetingJoinResponse object
                        return MeetingJoinResponse(
                            bot_id=data.get("id"),
                            status='joining',
                            meeting_url=str(request.meeting_url),
                            bot_name=request.bot_name,
                            success=True,
                            message="Successfully initiated bot to join meeting"
                        )
                    except ValueError as json_error:
                        return MeetingJoinResponse(
                            success=False,
                            message=f"Received successful response but failed to parse JSON: {str(json_error)}",
                            bot_id=None,
                            error_details={
                                "json_parse_error": str(json_error),
                                "response_text": response.text,
                                "status_code": response.status_code,
                            }
                        )
                else:
                    # Try to parse error response as JSON, fallback to text
                    try:
                        error_data = response.json() if response.content else {}
                    except ValueError:
                        error_data = {"raw_response": response.text}

                    return MeetingJoinResponse(
                        success=False,
                        message=f"Failed to join meeting: HTTP {response.status_code}",
                        bot_id=None,
                        error_details={
                            "status_code": response.status_code,
                            "response_data": error_data,
                            "response_text": response.text,
                        }
                    )

        except httpx.TimeoutException:
            return MeetingJoinResponse(
                success=False,
                message="Request timed out - Recall API may be slow or unavailable",
                bot_id=None,
                error_details={"exception": "TimeoutException"}
            )
        except httpx.ConnectError:
            return MeetingJoinResponse(
                success=False,
                message="Could not connect to Recall API - check network connectivity",
                bot_id=None,
                error_details={"exception": "ConnectError"}
            )
        except Exception as e:
            return MeetingJoinResponse(
                success=False,
                message=f"Unexpected error joining meeting: {str(e)}",
                bot_id=None,
                error_details={
                    "exception": str(e), 
                    "exception_type": type(e).__name__
                }
            )


# Create a global instance
recall_service = RecallService()


# Keep the old function for backward compatibility
async def join_meeting(request: MeetingJoinRequest):
    """Backward compatibility function"""
    return await recall_service.join_meeting(request)
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
import asyncio
import os
import aiohttp
import tempfile
import json

#from app.services.cloudinary_service import upload_to_cloudinary
from app.core.config import settings
from app.schemas.meeting import (
    MeetingJoinRequest,
    MeetingJoinResponse,
    TranscriptDetailResponse,
    MeetingPlatform,
    MeetingStatus,
    TranscriptChunk
)
from app.models.meeting import Meeting
from app.models.bot import Bot


class RecallAPIService:
    def __init__(self):
        self.api_key = settings.RECALL_API_KEY
        self.base_url = settings.RECALL_BASE_URL
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

    def _detect_meeting_platform(self, meeting_url: str) -> MeetingPlatform:
        """Detect meeting platform from URL"""
        url_lower = meeting_url.lower()

        if "zoom.us" in url_lower:
            return MeetingPlatform.ZOOM
        elif "meet.google.com" in url_lower:
            return MeetingPlatform.GOOGLE_MEET
        elif "teams.microsoft.com" in url_lower or "teams.live.com" in url_lower:
            return MeetingPlatform.MICROSOFT_TEAMS
        elif "webex.com" in url_lower:
            return MeetingPlatform.WEBEX
        else:
            return MeetingPlatform.OTHER

    async def join_meeting(self, request: MeetingJoinRequest) -> MeetingJoinResponse:
        """Join a meeting using the Recall API with enhanced transcript and audio configuration"""
        try:
            # Prepare the payload for Recall API according to official documentation
            payload = {
                "meeting_url": str(request.meeting_url),
                "recording_config": {
                    "transcript": {"provider": {"meeting_captions": {}}},
                    "audio_mixed_raw": {},
                },
            }

            # Add video recording if enabled
            if request.enable_video_recording:
                payload["recording_config"]["video_mixed_mp4"] = {}

            # Add bot name if provided
            if request.bot_name:
                payload["bot_name"] = request.bot_name
            
            # Add profile picture if provided (experimental - check Recall API docs)
            if hasattr(request, 'profile_picture') and request.profile_picture:
                payload["avatar_url"] = request.profile_picture

            # Add real-time endpoints for live processing if needed
            if (
                hasattr(request, "enable_realtime_processing")
                and request.enable_realtime_processing
            ):
                payload["recording_config"]["realtime_endpoints"] = [
                    {
                        "type": "websocket",
                        "url": f"{settings.RECALL_BASE_URL}/webhooks/realtime",
                        "events": [
                            "transcript.data",  # Real-time transcript events
                            "audio_mixed_raw.data",  # Real-time audio events
                        ],
                    }
                ]

            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/bot", headers=self.headers, json=payload
                )
                # Check if response is successful
                if response.status_code == 201:
                    try:
                        data = response.json()

                        return MeetingJoinResponse(
                            success=True,
                            message="Successfully initiated bot to join meeting",
                            bot_id=data.get("id"),
                            status="joining",
                            meeting_url=str(request.meeting_url),
                            bot_name=data.get("bot_name", request.bot_name)
                        )
                    except ValueError as json_error:
                        return MeetingJoinResponse(
                            success=False,
                            message=f"Received successful response but failed to parse JSON: {str(json_error)}",
                            bot_id=None,
                            status="error",
                            meeting_url=str(request.meeting_url),
                            bot_name=request.bot_name,
                            error_details={
                                "json_parse_error": str(json_error),
                                "response_text": response.text,
                                "status_code": response.status_code,
                            },
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
                        status="error", 
                        meeting_url=str(request.meeting_url),
                        bot_name=request.bot_name,
                        error_details={
                            "status_code": response.status_code,
                            "response_data": error_data,
                            "response_text": response.text,
                        },
                    )

        except httpx.TimeoutException:
            return MeetingJoinResponse(
                success=False,
                message="Request timed out - Recall API may be slow or unavailable",
                bot_id=None,
                status="error",
                meeting_url=str(request.meeting_url),
                bot_name=request.bot_name,
                error_details={"exception": "TimeoutException"},
            )
        except httpx.ConnectError:
            return MeetingJoinResponse(
                success=False,
                message="Could not connect to Recall API - check network connectivity",
                bot_id=None,
                status="error",
                meeting_url=str(request.meeting_url),
                bot_name=request.bot_name,
                error_details={"exception": "ConnectError"},
            )
        except Exception as e:
            return MeetingJoinResponse(
                success=False,
                message=f"Unexpected error joining meeting: {str(e)}",
                bot_id=None,
                status="error",
                meeting_url=str(request.meeting_url),
                bot_name=request.bot_name,
                error_details={"exception": str(e), "exception_type": type(e).__name__},
            )

    async def get_bot_status(self, bot_id: str) -> Dict[str, Any]:
        """Get the current status of a bot including transcript availability"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/bot/{bot_id}", headers=self.headers
                )

                if response.status_code == 200:
                    try:
                        bot_data = response.json()

                        # Add transcript availability information
                        bot_data["transcript_available"] = bool(
                            bot_data.get("status") == "completed"
                            and bot_data.get("transcript")
                        )

                        # Add media shortcuts for accessing recordings
                        if "media_shortcuts" in bot_data:
                            bot_data["recording_urls"] = {
                                "video": bot_data["media_shortcuts"]
                                .get("video_mixed", {})
                                .get("data", {})
                                .get("download_url"),
                                "audio": bot_data["media_shortcuts"]
                                .get("audio_mixed", {})
                                .get("data", {})
                                .get("download_url"),
                            }

                        return bot_data
                    except ValueError:
                        return {
                            "error": "Failed to parse response as JSON",
                            "raw_response": response.text,
                        }
                else:
                    return {
                        "error": f"Failed to get bot status: {response.status_code}",
                        "response_text": response.text,
                    }

        except Exception as e:
            return {"error": f"Error getting bot status: {str(e)}"}

    async def get_full_transcript(self, bot_id: str) -> Dict[str, Any]:
        """
        Get the complete stored transcript for a completed meeting
        According to Recall docs, transcripts are stored with the bot data
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get bot details which includes transcript data
                response = await client.get(
                    f"{self.base_url}/bot/{bot_id}", headers=self.headers
                )

                if response.status_code == 200:
                    try:
                        bot_data = response.json()

                        # Extract transcript from bot data
                        transcript_data = {
                            "bot_id": bot_id,
                            "status": bot_data.get("status"),
                            "transcript": bot_data.get("transcript", []),
                            "meeting_url": bot_data.get("meeting_url"),
                            "created_at": bot_data.get("created_at"),
                            "ended_at": bot_data.get("ended_at"),
                            "duration": bot_data.get("duration"),
                        }

                        # Process transcript chunks if available
                        processed_transcript = []
                        for item in transcript_data["transcript"]:
                            processed_transcript.append(
                                {
                                    "timestamp": item.get("timestamp"),
                                    "speaker": item.get("speaker"),
                                    "text": item.get("text"),
                                    "confidence": item.get("confidence"),
                                }
                            )

                        transcript_data["processed_transcript"] = processed_transcript
                        transcript_data["total_chunks"] = len(processed_transcript)

                        return transcript_data

                    except ValueError as e:
                        return {
                            "error": "Failed to parse transcript JSON",
                            "details": str(e),
                            "raw_response": response.text,
                        }
                else:
                    return {
                        "error": f"Failed to get transcript: {response.status_code}",
                        "response_text": response.text,
                    }

        except Exception as e:
            return {"error": f"Error getting transcript: {str(e)}"}

    async def store_transcript_locally(
        self, bot_id: str, storage_path: str = "transcripts/"
    ) -> Dict[str, Any]:
        """
        Retrieve and store transcript data locally for further processing
        """
        try:
            # Get the full transcript from Recall
            transcript_data = await self.get_full_transcript(bot_id)

            if "error" in transcript_data:
                return transcript_data

            # Create storage directory if it doesn't exist
            os.makedirs(storage_path, exist_ok=True)

            # Save transcript as JSON file
            filename = (
                f"{bot_id}_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            filepath = os.path.join(storage_path, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(transcript_data, f, indent=2, ensure_ascii=False, default=str)

            # Also save as plain text for easy reading
            text_filename = (
                f"{bot_id}_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            text_filepath = os.path.join(storage_path, text_filename)

            with open(text_filepath, "w", encoding="utf-8") as f:
                f.write(f"Meeting Transcript - Bot ID: {bot_id}\n")
                f.write(f"Meeting URL: {transcript_data.get('meeting_url', 'N/A')}\n")
                f.write(f"Created: {transcript_data.get('created_at', 'N/A')}\n")
                f.write(f"Duration: {transcript_data.get('duration', 'N/A')} seconds\n")
                f.write("=" * 80 + "\n\n")

                for chunk in transcript_data.get("processed_transcript", []):
                    timestamp = chunk.get("timestamp", "N/A")
                    speaker = chunk.get("speaker", "Unknown")
                    text = chunk.get("text", "")
                    f.write(f"[{timestamp}] {speaker}: {text}\n")

            return {
                "success": True,
                "json_file": filepath,
                "text_file": text_filepath,
                "total_chunks": transcript_data.get("total_chunks", 0),
                "message": f"Transcript stored successfully for bot {bot_id}",
            }

        except Exception as e:
            return {
                "error": f"Error storing transcript locally: {str(e)}",
                "bot_id": bot_id,
            }

    async def stop_bot(self, bot_id: str) -> Dict[str, Any]:
        """Stop a bot and end the meeting recording"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{self.base_url}/bot/{bot_id}", headers=self.headers
                )

                if response.status_code in [200, 204]:
                    return {"success": True, "message": "Bot stopped successfully"}
                else:
                    return {
                        "error": f"Failed to stop bot: {response.status_code}",
                        "response_text": response.text,
                    }

        except Exception as e:
            return {"error": f"Error stopping bot: {str(e)}"}

    async def get_transcript(self, bot_id: str) -> List[TranscriptChunk]:
        """Get the transcript for a completed meeting"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/bot/{bot_id}/transcript", headers=self.headers
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                        transcript_chunks = []

                        for item in data.get("transcript", []):
                            chunk = TranscriptChunk(
                                timestamp=datetime.fromisoformat(
                                    item.get("timestamp", "")
                                ),
                                speaker=item.get("speaker", "Unknown"),
                                text=item.get("text", ""),
                                confidence=item.get("confidence"),
                            )
                            transcript_chunks.append(chunk)

                        return transcript_chunks
                    except ValueError:
                        print(f"Failed to parse transcript JSON: {response.text}")
                        return []
                else:
                    print(
                        f"Failed to get transcript: {response.status_code} - {response.text}"
                    )
                    return []

        except Exception as e:
            print(f"Error getting transcript: {str(e)}")
            return []

    async def list_bots(self) -> List[Dict[str, Any]]:
        """List all bots"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/bot", headers=self.headers
                )

                if response.status_code == 200:
                    try:
                        return response.json().get("results", [])
                    except ValueError:
                        print(f"Failed to parse bots list JSON: {response.text}")
                        return []
                else:
                    print(
                        f"Failed to list bots: {response.status_code} - {response.text}"
                    )
                    return []

        except Exception as e:
            print(f"Error listing bots: {str(e)}")
            return []

    async def list_recordings(
        self, bot_id: Optional[str] = None, limit: int = 50
    ) -> Dict[str, Any]:
        """
        List recordings using the official recordings endpoint
        https://docs.recall.ai/reference/recording_list
        """
        try:
            params = {"limit": limit}
            if bot_id:
                params["bot_id"] = bot_id

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/recording/", headers=self.headers, params=params
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                        return {
                            "success": True,
                            "recordings": data.get("results", []),
                            "count": data.get("count", 0),
                            "next": data.get("next"),
                            "previous": data.get("previous"),
                        }
                    except ValueError as e:
                        return {
                            "error": "Failed to parse recordings JSON",
                            "details": str(e),
                            "raw_response": response.text,
                        }
                else:
                    return {
                        "error": f"Failed to list recordings: {response.status_code}",
                        "response_text": response.text,
                    }

        except Exception as e:
            return {"error": f"Error listing recordings: {str(e)}"}

    async def list_transcripts(
        self,
        bot_id: Optional[str] = None,
        recording_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        List transcripts using the official transcript endpoint
        https://docs.recall.ai/reference/transcript_list
        """
        try:
            params = {"limit": limit}
            if bot_id:
                params["bot_id"] = bot_id
            if recording_id:
                params["recording_id"] = recording_id

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/transcript/", headers=self.headers, params=params
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                        return {
                            "success": True,
                            "transcripts": data.get("results", []),
                            "count": data.get("count", 0),
                            "next": data.get("next"),
                            "previous": data.get("previous"),
                        }
                    except ValueError as e:
                        return {
                            "error": "Failed to parse transcripts JSON",
                            "details": str(e),
                            "raw_response": response.text,
                        }
                else:
                    return {
                        "error": f"Failed to list transcripts: {response.status_code}",
                        "response_text": response.text,
                    }

        except Exception as e:
            return {"error": f"Error listing transcripts: {str(e)}"}

    async def get_transcript_by_id(self, transcript_id: str) -> Dict[str, Any]:
        """
        Retrieve a specific transcript by ID using the official endpoint
        https://docs.recall.ai/reference/transcript_retrieve
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/transcript/{transcript_id}/", headers=self.headers
                )

                if response.status_code == 200:
                    try:
                        transcript_data = response.json()

                        # Process transcript chunks for easier use
                        processed_chunks = []
                        transcript_words = transcript_data.get("words", [])

                        for word in transcript_words:
                            processed_chunks.append(
                                {
                                    "start": word.get("start"),
                                    "end": word.get("end"),
                                    "text": word.get("text"),
                                    "speaker": word.get("speaker"),
                                    "confidence": word.get("confidence"),
                                }
                            )

                        return {
                            "success": True,
                            "transcript_id": transcript_id,
                            "transcript_data": transcript_data,
                            "processed_chunks": processed_chunks,
                            "total_words": len(transcript_words),
                            "duration": transcript_data.get("duration"),
                            "status": transcript_data.get("status"),
                        }

                    except ValueError as e:
                        return {
                            "error": "Failed to parse transcript JSON",
                            "details": str(e),
                            "raw_response": response.text,
                        }
                else:
                    return {
                        "error": f"Failed to get transcript: {response.status_code}",
                        "response_text": response.text,
                    }

        except Exception as e:
            return {"error": f"Error getting transcript: {str(e)}"}

    async def list_meeting_metadata(
        self, bot_id: Optional[str] = None, limit: int = 50
    ) -> Dict[str, Any]:
        """
        List meeting metadata using the official meeting_metadata endpoint
        https://docs.recall.ai/reference/meeting_metadata_list
        """
        try:
            params = {"limit": limit}
            if bot_id:
                params["bot_id"] = bot_id

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/meeting_metadata/",
                    headers=self.headers,
                    params=params,
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                        return {
                            "success": True,
                            "meeting_metadata": data.get("results", []),
                            "count": data.get("count", 0),
                            "next": data.get("next"),
                            "previous": data.get("previous"),
                        }
                    except ValueError as e:
                        return {
                            "error": "Failed to parse meeting metadata JSON",
                            "details": str(e),
                            "raw_response": response.text,
                        }
                else:
                    return {
                        "error": f"Failed to list meeting metadata: {response.status_code}",
                        "response_text": response.text,
                    }

        except Exception as e:
            return {"error": f"Error listing meeting metadata: {str(e)}"}

    async def get_meeting_metadata_by_id(self, metadata_id: str) -> Dict[str, Any]:
        """
        Retrieve specific meeting metadata by ID
        https://docs.recall.ai/reference/meeting_metadata_retrieve
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/meeting_metadata/{metadata_id}/",
                    headers=self.headers,
                )

                if response.status_code == 200:
                    try:
                        metadata = response.json()
                        return {
                            "success": True,
                            "metadata_id": metadata_id,
                            "meeting_metadata": metadata,
                            "participants": metadata.get("participants", []),
                            "title": metadata.get("title"),
                            "start_time": metadata.get("start_time"),
                            "end_time": metadata.get("end_time"),
                        }
                    except ValueError as e:
                        return {
                            "error": "Failed to parse meeting metadata JSON",
                            "details": str(e),
                            "raw_response": response.text,
                        }
                else:
                    return {
                        "error": f"Failed to get meeting metadata: {response.status_code}",
                        "response_text": response.text,
                    }

        except Exception as e:
            return {"error": f"Error getting meeting metadata: {str(e)}"}

    async def get_comprehensive_meeting_data(self, bot_id: str) -> Dict[str, Any]:
        """
        Get comprehensive meeting data using all official endpoints
        Combines recordings, transcripts, and metadata for a complete picture
        """
        try:
            # Get all data in parallel for better performance
            recordings_task = self.list_recordings(bot_id=bot_id)
            transcripts_task = self.list_transcripts(bot_id=bot_id)
            metadata_task = self.list_meeting_metadata(bot_id=bot_id)
            bot_status_task = self.get_bot_status(bot_id)
            # Wait for all tasks to complete
            (
                recordings_result,
                transcripts_result,
                metadata_result,
                bot_status,
            ) = await asyncio.gather(
                recordings_task,
                transcripts_task,
                metadata_task,
                bot_status_task,
                return_exceptions=True,
            )
            # Compile comprehensive data
            comprehensive_data = {
                "bot_id": bot_id,
                "success": True,
                "data_retrieved_at": datetime.utcnow().isoformat(),
            }
            # Add bot status
            if not isinstance(bot_status, Exception) and "error" not in bot_status:
                comprehensive_data["bot_status"] = bot_status
            else:
                comprehensive_data["bot_status_error"] = str(bot_status)
            # Add recordings data
            if not isinstance(recordings_result, Exception) and recordings_result.get("success"):
                comprehensive_data["recordings"] = recordings_result["recordings"]
                comprehensive_data["recordings_count"] = recordings_result["count"]
                
                # Cloudinary Upload Integration
                first_recording = recordings_result["recordings"][0] if recordings_result["recordings"] else None
                if first_recording:
                    download_url = first_recording.get("download_url")
                    if download_url:
                        tmp_path = None
                        try:
                            # Validate URL format
                            if not download_url.startswith(('http://', 'https://')):
                                raise ValueError("Invalid download URL format")
                            
                            async with aiohttp.ClientSession() as session, \
                                     session.get(download_url) as video_resp:
                                video_resp.raise_for_status()  # Raise on HTTP errors
                                video_bytes = await video_resp.read()
                                
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                                    tmp_file.write(video_bytes)
                                    tmp_path = tmp_file.name
                            
                            # Upload to Cloudinary (commented out - service not available)
                            # upload_result = upload_to_cloudinary(tmp_path)
                            # if upload_result.get("success"):
                            #     comprehensive_data["cloudinary_video_url"] = upload_result["url"]
                            # else:
                            #     comprehensive_data["cloudinary_upload_error"] = upload_result.get("error")
                            comprehensive_data["cloudinary_upload_error"] = "Cloudinary service not configured"
                        except aiohttp.ClientError as e:
                            comprehensive_data["cloudinary_upload_error"] = f"Download failed: {str(e)}"
                        except Exception as e:
                            comprehensive_data["cloudinary_upload_error"] = str(e)
                        finally:
                            # Ensure temp file is always cleaned up
                            if tmp_path and os.path.exists(tmp_path):
                                os.remove(tmp_path)
                    else:
                        comprehensive_data["cloudinary_upload_error"] = "No download URL available."
                else:
                    comprehensive_data["cloudinary_upload_error"] = "No recordings available to upload."

            # Add transcripts data
            if not isinstance(transcripts_result, Exception) and transcripts_result.get("success"):
                comprehensive_data["transcripts"] = transcripts_result["transcripts"]
                comprehensive_data["transcripts_count"] = transcripts_result["count"]
                # If we have transcripts, get detailed data for the first one
                if transcripts_result["transcripts"]:
                    first_transcript = transcripts_result["transcripts"][0]
                    transcript_id = first_transcript.get("id")
                    if transcript_id:
                        detailed_transcript = await self.get_transcript_by_id(transcript_id)
                        if detailed_transcript.get("success"):
                            comprehensive_data["detailed_transcript"] = detailed_transcript
            else:
                comprehensive_data["transcripts_error"] = str(transcripts_result)
            # Add meeting metadata
            if not isinstance(metadata_result, Exception) and metadata_result.get("success"):
                comprehensive_data["meeting_metadata"] = metadata_result["meeting_metadata"]
                comprehensive_data["metadata_count"] = metadata_result["count"]
                # If we have metadata, get detailed data for the first one
                if metadata_result["meeting_metadata"]:
                    first_metadata = metadata_result["meeting_metadata"][0]
                    metadata_id = first_metadata.get("id")
                    if metadata_id:
                        detailed_metadata = await self.get_meeting_metadata_by_id(metadata_id)
                        if detailed_metadata.get("success"):
                            comprehensive_data["detailed_metadata"] = detailed_metadata
            else:
                comprehensive_data["metadata_error"] = str(metadata_result)
            return comprehensive_data
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting comprehensive meeting data: {str(e)}",
                "bot_id": bot_id,
            } 
        
        
    # async def get_comprehensive_meeting_data(self, bot_id: str) -> Dict[str, Any]:
    #     """
    #     Get comprehensive meeting data using all official endpoints
    #     Combines recordings, transcripts, and metadata for a complete picture
    #     """
    #     try:
    #         # Get all data in parallel for better performance
    #         recordings_task = self.list_recordings(bot_id=bot_id)
    #         transcripts_task = self.list_transcripts(bot_id=bot_id)
    #         metadata_task = self.list_meeting_metadata(bot_id=bot_id)
    #         bot_status_task = self.get_bot_status(bot_id)

    #         # Wait for all tasks to complete
    #         (
    #             recordings_result,
    #             transcripts_result,
    #             metadata_result,
    #             bot_status,
    #         ) = await asyncio.gather(
    #             recordings_task,
    #             transcripts_task,
    #             metadata_task,
    #             bot_status_task,
    #             return_exceptions=True,
    #         )

    #         # Compile comprehensive data
    #         comprehensive_data = {
    #             "bot_id": bot_id,
    #             "success": True,
    #             "data_retrieved_at": datetime.utcnow().isoformat(),
    #         }

    #         # Add bot status
    #         if not isinstance(bot_status, Exception) and "error" not in bot_status:
    #             comprehensive_data["bot_status"] = bot_status
    #         else:
    #             comprehensive_data["bot_status_error"] = str(bot_status)

    #         # Add recordings data
    #         if not isinstance(recordings_result, Exception) and recordings_result.get(
    #             "success"
    #         ):
    #             comprehensive_data["recordings"] = recordings_result["recordings"]
    #             comprehensive_data["recordings_count"] = recordings_result["count"]
    #         else:
    #             comprehensive_data["recordings_error"] = str(recordings_result)

    #         # Add transcripts data
    #         if not isinstance(transcripts_result, Exception) and transcripts_result.get(
    #             "success"
    #         ):
    #             comprehensive_data["transcripts"] = transcripts_result["transcripts"]
    #             comprehensive_data["transcripts_count"] = transcripts_result["count"]

    #             # If we have transcripts, get detailed data for the first one
    #             if transcripts_result["transcripts"]:
    #                 first_transcript = transcripts_result["transcripts"][0]
    #                 transcript_id = first_transcript.get("id")
    #                 if transcript_id:
    #                     detailed_transcript = await self.get_transcript_by_id(
    #                         transcript_id
    #                     )
    #                     if detailed_transcript.get("success"):
    #                         comprehensive_data["detailed_transcript"] = (
    #                             detailed_transcript
    #                         )
    #         else:
    #             comprehensive_data["transcripts_error"] = str(transcripts_result)

    #         # Add meeting metadata
    #         if not isinstance(metadata_result, Exception) and metadata_result.get(
    #             "success"
    #         ):
    #             comprehensive_data["meeting_metadata"] = metadata_result[
    #                 "meeting_metadata"
    #             ]
    #             comprehensive_data["metadata_count"] = metadata_result["count"]

    #             # If we have metadata, get detailed data for the first one
    #             if metadata_result["meeting_metadata"]:
    #                 first_metadata = metadata_result["meeting_metadata"][0]
    #                 metadata_id = first_metadata.get("id")
    #                 if metadata_id:
    #                     detailed_metadata = await self.get_meeting_metadata_by_id(
    #                         metadata_id
    #                     )
    #                     if detailed_metadata.get("success"):
    #                         comprehensive_data["detailed_metadata"] = detailed_metadata
    #         else:
    #             comprehensive_data["metadata_error"] = str(metadata_result)

    #         return comprehensive_data

    #     except Exception as e:
    #         return {
    #             "success": False,
    #             "error": f"Error getting comprehensive meeting data: {str(e)}",
    #             "bot_id": bot_id,
    #         }

    async def store_comprehensive_transcript(
        self, bot_id: str, storage_path: str = "transcripts/"
    ) -> Dict[str, Any]:
        """
        Enhanced transcript storage using official endpoints
        Combines transcript data with recordings and metadata
        """
        try:
            # Get comprehensive data using official endpoints
            comprehensive_data = await self.get_comprehensive_meeting_data(bot_id)

            if not comprehensive_data.get("success"):
                return comprehensive_data

            # Create storage directory
            os.makedirs(storage_path, exist_ok=True)

            # Generate filenames with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"{bot_id}_comprehensive_{timestamp}"

            # Save comprehensive data as JSON
            json_filepath = os.path.join(storage_path, f"{base_filename}.json")
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(
                    comprehensive_data, f, indent=2, ensure_ascii=False, default=str
                )

            # Create human-readable transcript if available
            text_filepath = None
            if "detailed_transcript" in comprehensive_data:
                text_filepath = os.path.join(storage_path, f"{base_filename}.txt")
                transcript_data = comprehensive_data["detailed_transcript"]

                with open(text_filepath, "w", encoding="utf-8") as f:
                    f.write(f"Comprehensive Meeting Data - Bot ID: {bot_id}\n")
                    f.write(f"Retrieved: {comprehensive_data['data_retrieved_at']}\n")
                    f.write("=" * 80 + "\n\n")

                    # Add metadata if available
                    if "detailed_metadata" in comprehensive_data:
                        metadata = comprehensive_data["detailed_metadata"][
                            "meeting_metadata"
                        ]
                        f.write(f"Meeting Title: {metadata.get('title', 'N/A')}\n")
                        f.write(f"Start Time: {metadata.get('start_time', 'N/A')}\n")
                        f.write(f"End Time: {metadata.get('end_time', 'N/A')}\n")
                        f.write(
                            f"Participants: {len(metadata.get('participants', []))}\n"
                        )
                        f.write("-" * 80 + "\n\n")

                    # Add transcript content
                    f.write("TRANSCRIPT:\n")
                    f.write("-" * 40 + "\n")

                    processed_chunks = transcript_data.get("processed_chunks", [])
                    for chunk in processed_chunks:
                        start_time = chunk.get("start", "N/A")
                        speaker = chunk.get("speaker", "Unknown")
                        text = chunk.get("text", "")
                        f.write(f"[{start_time}s] {speaker}: {text}\n")

            return {
                "success": True,
                "bot_id": bot_id,
                "json_file": json_filepath,
                "text_file": text_filepath,
                "comprehensive_data": True,
                "recordings_count": comprehensive_data.get("recordings_count", 0),
                "transcripts_count": comprehensive_data.get("transcripts_count", 0),
                "metadata_count": comprehensive_data.get("metadata_count", 0),
                "message": f"Comprehensive meeting data stored for bot {bot_id}",
            }

        except Exception as e:
            return {
                "error": f"Error storing comprehensive transcript: {str(e)}",
                "bot_id": bot_id,
            }

    async def fetch_and_format_transcript_from_url(self, download_url: str) -> Dict[str, Any]:
        """
        Fetch transcript data from download URL and format it in a readable way
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(download_url)
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Failed to fetch transcript: HTTP {response.status_code}",
                        "download_url": download_url
                    }
                
                # Parse the JSON response
                try:
                    raw_transcript_data = response.json()
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"Failed to parse transcript JSON: {str(e)}",
                        "raw_response": response.text[:500]
                    }
                
                # Format the transcript data
                formatted_transcript = self._format_transcript_data(raw_transcript_data)
                
                return {
                    "success": True,
                    "download_url": download_url,
                    "raw_transcript": raw_transcript_data,
                    "formatted_transcript": formatted_transcript,
                    "statistics": self._calculate_transcript_statistics(raw_transcript_data)
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error fetching transcript: {str(e)}",
                "download_url": download_url
            }
    
    def _format_transcript_data(self, raw_data: List[Dict]) -> Dict[str, Any]:
        """
        Format raw transcript data into a readable structure
        """
        formatted_chunks = []
        continuous_text = []
        participants = {}
        
        for chunk in raw_data:
            participant_info = chunk.get("participant", {})
            participant_id = participant_info.get("id")
            participant_name = participant_info.get("name", "Unknown")
            is_host = participant_info.get("is_host", False)
            
            # Track unique participants
            if participant_id not in participants:
                participants[participant_id] = {
                    "name": participant_name,
                    "is_host": is_host,
                    "platform": participant_info.get("platform", "unknown"),
                    "total_words": 0,
                    "total_speaking_time": 0.0
                }
            
            # Process words in this chunk
            words = chunk.get("words", [])
            for word_info in words:
                text = word_info.get("text", "")
                start_time = word_info.get("start_timestamp", {})
                end_time = word_info.get("end_timestamp", {})

                start_relative = start_time.get("relative", 0)
                end_relative = end_time.get("relative", 0)
                start_absolute = start_time.get("absolute", "")
                end_absolute = end_time.get("absolute", "")
                
                # Format timestamps
                start_formatted = self._format_timestamp(start_relative)
                end_formatted = self._format_timestamp(end_relative)
                duration = end_relative - start_relative
                
                formatted_chunk = {
                    "participant_id": participant_id,
                    "participant_name": participant_name,
                    "is_host": is_host,
                    "text": text,
                    "start_time": start_formatted,
                    "end_time": end_formatted,
                    "duration": f"{duration:.2f}s",
                    "start_relative": start_relative,
                    "end_relative": end_relative,
                    "start_absolute": start_absolute,
                    "end_absolute": end_absolute
                }
                
                formatted_chunks.append(formatted_chunk)
                
                # Update participant statistics
                participants[participant_id]["total_words"] += len(text.split())
                participants[participant_id]["total_speaking_time"] += duration
                
                # Add to continuous text
                continuous_text.append(f"[{start_formatted}] {participant_name}: {text}")
        
        # Sort chunks by start time
        formatted_chunks.sort(key=lambda x: x["start_relative"])
        
        return {
            "chunks": formatted_chunks,
            "continuous_text": "\n".join(continuous_text),
            "participants": participants,
            "total_chunks": len(formatted_chunks)
        }
    
    def _calculate_transcript_statistics(self, raw_data: List[Dict]) -> Dict[str, Any]:
        """
        Calculate statistics from the transcript data
        """
        if not raw_data:
            return {}
        
        total_words = 0
        total_duration = 0.0
        participants_count = set()
        earliest_time = None
        latest_time = None
        
        for chunk in raw_data:
            participant_id = chunk.get("participant", {}).get("id")
            if participant_id:
                participants_count.add(participant_id)
            
            words = chunk.get("words", [])
            for word_info in words:
                # Count words
                text = word_info.get("text", "")
                total_words += len(text.split())
                
                # Calculate duration
                start_time = word_info.get("start_timestamp", {}).get("relative", 0)
                end_time = word_info.get("end_timestamp", {}).get("relative", 0)
                
                if earliest_time is None or start_time < earliest_time:
                    earliest_time = start_time
                if latest_time is None or end_time > latest_time:
                    latest_time = end_time
        
        if earliest_time is not None and latest_time is not None:
            total_duration = latest_time - earliest_time
        
        return {
            "total_words": total_words,
            "total_duration_seconds": total_duration,
            "total_duration_formatted": self._format_timestamp(total_duration),
            "participants_count": len(participants_count),
            "words_per_minute": round((total_words / (total_duration / 60)) if total_duration > 0 else 0, 2)
        }
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format seconds into MM:SS format
        """
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes:02d}:{remaining_seconds:02d}"

    async def get_bot_recordings(self, bot_id: str) -> RecordingResponse:
        """
        Fetch recordings for a specific bot from Recall API
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/bot/{bot_id}/",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    recordings = data.get("recordings", [])
                    
                    if recordings:
                        recording_info_list = []
                        download_url = None
                        
                        for recording in recordings:
                            # Parse recording data
                            recording_info = {
                                "id": recording.get("id"),
                                "created_at": recording.get("created_at"),
                                "started_at": recording.get("started_at"),
                                "completed_at": recording.get("completed_at"),
                                "expires_at": recording.get("expires_at"),
                                "status": recording.get("status", {}),
                                "media_shortcuts": recording.get("media_shortcuts", {})
                            }
                            recording_info_list.append(recording_info)
                            
                            # Extract video download URL if available
                            media_shortcuts = recording.get("media_shortcuts", {})
                            video_mixed = media_shortcuts.get("video_mixed", {})
                            if video_mixed and video_mixed.get("data", {}).get("download_url"):
                                download_url = video_mixed["data"]["download_url"]
                        
                        return RecordingResponse(
                            success=True,
                            message="Recordings retrieved successfully",
                            bot_id=bot_id,
                            recordings=[RecordingInfo(**info) for info in recording_info_list],
                            download_url=download_url
                        )
                    else:
                        return RecordingResponse(
                            success=True,
                            message="No recordings found for this bot",
                            bot_id=bot_id,
                            recordings=[]
                        )
                else:
                    try:
                        error_data = response.json() if response.content else {}
                    except ValueError:
                        error_data = {"raw_response": response.text}
                    
                    return RecordingResponse(
                        success=False,
                        message=f"Failed to retrieve recordings: HTTP {response.status_code}",
                        bot_id=bot_id,
                        error_details={
                            "status_code": response.status_code,
                            "response_data": error_data,
                            "response_text": response.text,
                        }
                    )
                    
        except httpx.TimeoutException:
            return RecordingResponse(
                success=False,
                message="Request timed out - Recall API may be slow or unavailable",
                bot_id=bot_id,
                error_details={"exception": "TimeoutException"}
            )
        except httpx.ConnectError:
            return RecordingResponse(
                success=False,
                message="Could not connect to Recall API - check network connectivity",
                bot_id=bot_id,
                error_details={"exception": "ConnectError"}
            )
        except Exception as e:
            return RecordingResponse(
                success=False,
                message=f"Unexpected error retrieving recordings: {str(e)}",
                bot_id=bot_id,
                error_details={"exception": str(e)}
            )

    async def download_recording(self, download_url: str, local_path: str) -> bool:
        """
        Download a recording file from the provided URL to local storage
        """
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:  # Longer timeout for file downloads
                response = await client.get(download_url, follow_redirects=True)
                
                if response.status_code == 200:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    
                    # Write file to disk
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                    
                    return True
                else:
                    print(f"Failed to download recording: HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"Error downloading recording: {str(e)}")
            return False

    # Recording Management Methods (moved from recording_service.py)
    async def update_bot_recording_status(self, bot_id: str, db) -> Optional[Any]:
        """
        Update bot recording status by fetching latest data from Recall API
        """
        try:
            # Import here to avoid circular import
            from app.models.bot import Bot
            
            # Fetch recording data from Recall API
            recording_response = await self.get_bot_recordings(bot_id)
            
            # Find bot in database
            bot = db.query(Bot).filter(Bot.bot_id == bot_id).first()
            if not bot:
                print(f"Bot with ID {bot_id} not found in database")
                return None
            
            if recording_response.success and recording_response.recordings:
                # Update bot with recording information
                latest_recording = recording_response.recordings[0]  # Get the most recent recording
                
                # Update recording status based on the API response
                api_status = latest_recording.status.get("code", "unknown")
                if api_status == "done":
                    bot.recording_status = "completed"
                elif api_status == "in_progress":
                    bot.recording_status = "recording"
                elif api_status == "failed":
                    bot.recording_status = "failed"
                else:
                    bot.recording_status = "unknown"
                
                # Store recording metadata
                bot.recording_data = latest_recording.dict()
                
                # Extract download URL if available
                if hasattr(latest_recording, 'media_shortcuts') and latest_recording.media_shortcuts:
                    video_data = latest_recording.media_shortcuts.get('video_mixed', {}).get('data', {})
                    if video_data and 'download_url' in video_data:
                        bot.video_recording_url = video_data['download_url']
                        
                # Set expiration date
                if hasattr(latest_recording, 'expires_at'):
                    bot.recording_expires_at = latest_recording.expires_at
                
                db.commit()
                return bot
            
            return bot
            
        except Exception as e:
            print(f"Error updating bot recording status: {str(e)}")
            return None

    async def download_and_store_recording(self, bot_id: str, db, base_path: str = "recordings/generated") -> Optional[str]:
        """
        Download and store recording locally for a bot
        """
        try:
            from app.models.bot import Bot
            import os
            
            # Get bot from database
            bot = db.query(Bot).filter(Bot.bot_id == bot_id).first()
            if not bot or not bot.video_recording_url:
                print(f"No bot or recording URL found for bot_id: {bot_id}")
                return None
            
            # Create local file path
            os.makedirs(base_path, exist_ok=True)
            local_filename = f"{bot_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
            local_path = os.path.join(base_path, local_filename)
            
            # Download the file
            success = await self.download_recording(bot.video_recording_url, local_path)
            
            if success:
                # Update bot with local file path
                bot.video_download_url = local_path
                bot.recording_status = "downloaded"
                db.commit()
                
                print(f"Successfully downloaded recording for bot {bot_id} to {local_path}")
                return local_path
            else:
                print(f"Failed to download recording for bot {bot_id}")
                return None
                
        except Exception as e:
            print(f"Error downloading and storing recording: {str(e)}")
            return None

    def get_recording_status(self, bot_id: str, db) -> Dict[str, Any]:
        """
        Get recording status and information for a bot
        """
        try:
            from app.models.bot import Bot
            import os
            
            bot = db.query(Bot).filter(Bot.bot_id == bot_id).first()
            if not bot:
                return {"error": "Bot not found"}
            
            return {
                "bot_id": bot.bot_id,
                "recording_status": bot.recording_status,
                "video_recording_url": bot.video_recording_url,
                "video_download_url": bot.video_download_url,
                "recording_expires_at": bot.recording_expires_at.isoformat() if bot.recording_expires_at else None,
                "recording_data": bot.recording_data,
                "has_local_file": bool(bot.video_download_url and os.path.exists(bot.video_download_url))
            }
            
        except Exception as e:
            return {"error": f"Error getting recording status: {str(e)}"}

    async def process_completed_recording(self, bot_id: str, db) -> bool:
        """
        Process a completed recording (update status and optionally download)
        """
        try:
            # Update recording status from API
            bot = await self.update_bot_recording_status(bot_id, db)
            if not bot:
                return False
            
            # If recording is completed and we have a URL, download it
            if bot.recording_status == "completed" and bot.video_recording_url:
                local_path = await self.download_and_store_recording(bot_id, db)
                return bool(local_path)
            
            return True
            
        except Exception as e:
            print(f"Error processing completed recording: {str(e)}")
            return False

    def get_local_recording_path(self, bot_id: str, db) -> Optional[str]:
        """
        Get the local file path for a bot's recording if it exists
        """
        try:
            from app.models.bot import Bot
            import os
            
            bot = db.query(Bot).filter(Bot.bot_id == bot_id).first()
            if bot and bot.video_download_url and os.path.exists(bot.video_download_url):
                return bot.video_download_url
            return None
        except Exception as e:
            print(f"Error getting local recording path: {str(e)}")
            return None

    async def check_and_update_expired_recordings(self, db) -> List[str]:
        """
        Check for expired recording URLs and update their status
        """
        try:
            from app.models.bot import Bot
            from sqlalchemy import and_
            
            # Find bots with recording URLs that might be expired
            current_time = datetime.utcnow()
            expired_bots = db.query(Bot).filter(
                and_(
                    Bot.recording_expires_at.isnot(None),
                    Bot.recording_expires_at < current_time,
                    Bot.video_recording_url.isnot(None)
                )
            ).all()
            
            expired_bot_ids = []
            for bot in expired_bots:
                # Clear expired URL
                bot.video_recording_url = None
                bot.recording_status = "expired"
                expired_bot_ids.append(bot.bot_id)
                print(f"Marked recording as expired for bot {bot.bot_id}")
            
            if expired_bot_ids:
                db.commit()
            
            return expired_bot_ids
            
        except Exception as e:
            print(f"Error checking expired recordings: {str(e)}")
            db.rollback()
            return []# Global service instance
recall_service = RecallAPIService()

"""
Google Calendar service for webhook management and event synchronization
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
import httpx
import logging

from app.core.config import settings
from app.models.user import User
from app.models.calendar_event import CalendarEvent
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingPlatform

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Service for managing Google Calendar webhooks and events"""
    
    def __init__(self):
        self.webhook_base_url = getattr(settings, 'WEBHOOK_BASE_URL', 'http://localhost:8000')
        
    def _get_calendar_service(self, user: User):
        """Get authenticated Google Calendar service for user"""
        if not user.oauth_tokens:
            raise ValueError("User has no Google credentials")
            
        credentials = Credentials(
            token=user.oauth_tokens.get('access_token'),
            refresh_token=user.oauth_tokens.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        
        return build('calendar', 'v3', credentials=credentials)
    
    async def setup_calendar_webhook(self, user: User, db: Session) -> Dict[str, Any]:
        """Set up Google Calendar webhook for user"""
        try:
            service = self._get_calendar_service(user)
            
            # Generate unique channel ID for this user
            channel_id = f"calendar-webhook-{user.id}-{uuid.uuid4()}"
            webhook_url = f"{self.webhook_base_url}/api/v1/calendar/webhook"
            
            # Set up the watch request
            watch_request = {
                'id': channel_id,
                'type': 'web_hook',
                'address': webhook_url,
                'token': str(user.id),  # Use user ID as verification token
                'expiration': int((datetime.utcnow() + timedelta(days=7)).timestamp() * 1000)  # 7 days from now
            }
            
            # Create the watch on the primary calendar
            result = service.events().watch(
                calendarId='primary',
                body=watch_request
            ).execute()
            
            # Store webhook info in user's oauth_tokens
            if not user.oauth_tokens:
                user.oauth_tokens = {}
            
            user.oauth_tokens['calendar_webhook'] = {
                'channel_id': channel_id,
                'resource_id': result.get('resourceId'),
                'expiration': result.get('expiration'),
                'created_at': datetime.utcnow().isoformat()
            }
            
            db.commit()
            
            logger.info(f"Calendar webhook set up for user {user.id}")
            return {
                'success': True,
                'channel_id': channel_id,
                'resource_id': result.get('resourceId'),
                'expiration': result.get('expiration')
            }
            
        except HttpError as e:
            logger.error(f"Google API error setting up webhook: {e}")
            raise Exception(f"Failed to set up calendar webhook: {e}")
        except Exception as e:
            logger.error(f"Error setting up calendar webhook: {e}")
            raise
    
    async def stop_calendar_webhook(self, user: User, db: Session) -> bool:
        """Stop Google Calendar webhook for user"""
        try:
            if not user.oauth_tokens or 'calendar_webhook' not in user.oauth_tokens:
                logger.warning(f"No webhook found for user {user.id}")
                return False
                
            service = self._get_calendar_service(user)
            webhook_info = user.oauth_tokens['calendar_webhook']
            
            # Stop the webhook
            service.channels().stop(body={
                'id': webhook_info['channel_id'],
                'resourceId': webhook_info['resource_id']
            }).execute()
            
            # Remove webhook info from user oauth_tokens
            del user.oauth_tokens['calendar_webhook']
            db.commit()
            
            logger.info(f"Calendar webhook stopped for user {user.id}")
            return True
            
        except HttpError as e:
            logger.error(f"Google API error stopping webhook: {e}")
            return False
        except Exception as e:
            logger.error(f"Error stopping calendar webhook: {e}")
            return False
    
    async def handle_calendar_notification(self, headers: Dict[str, str], user_id: int, db: Session) -> bool:
        """Handle incoming calendar webhook notification"""
        try:
            # Convert headers to lowercase for case-insensitive lookup
            headers_lower = {k.lower(): v for k, v in headers.items()}
            
            # Verify the notification is valid
            resource_id = headers_lower.get('x-goog-resource-id')
            resource_state = headers_lower.get('x-goog-resource-state')
            channel_token = headers_lower.get('x-goog-channel-token')
            
            logger.info(f"Processing webhook - Resource ID: {resource_id}, State: {resource_state}, Token: {channel_token}")
            
            if not all([resource_id, resource_state, channel_token]):
                logger.warning(f"Invalid webhook notification - missing headers. Available headers: {list(headers_lower.keys())}")
                return False
            
            # Verify token matches user ID
            if channel_token != str(user_id):
                logger.warning(f"Invalid token in webhook notification: {channel_token}")
                return False
            
            # Get user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found for webhook notification")
                return False
            
            # Only process sync events (not initial sync)
            if resource_state == 'sync':
                logger.info("Received sync notification - ignoring")
                return True
            
            # Sync calendar events for this user
            await self.sync_user_calendar_events(user, db)
            
            logger.info(f"Successfully processed calendar notification for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling calendar notification: {e}")
            return False
    
    async def sync_user_calendar_events(self, user: User, db: Session) -> Dict[str, Any]:
        """Sync user's calendar events and create/update meetings"""
        try:
            service = self._get_calendar_service(user)
            
            # Get events from the last day to next 30 days
            now = datetime.utcnow()
            time_min = (now - timedelta(days=1)).isoformat() + 'Z'
            time_max = (now + timedelta(days=30)).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            created_meetings = []
            processed_events = []
            
            for event in events:
                try:
                    event_result = await self._process_calendar_event(event, user, db)
                    if event_result:
                        if event_result.get('created_meeting'):
                            created_meetings.append(event_result)
                        processed_events.append(event_result)
                except Exception as event_error:
                    logger.error(f"Error processing individual event {event.get('id', 'unknown')}: {event_error}")
                    # Continue processing other events
                    continue
            
            try:
                db.commit()
                logger.info(f"Processed {len(processed_events)} calendar events, created {len(created_meetings)} meetings for user {user.id}")
            except Exception as commit_error:
                logger.error(f"Error committing calendar sync for user {user.id}: {commit_error}")
                db.rollback()
                raise
            
            return {
                'total_events_processed': len(processed_events),
                'meetings_created': len(created_meetings),
                'events': processed_events,
                'meetings_with_urls': created_meetings
            }
            
        except Exception as e:
            logger.error(f"Error syncing calendar events for user {user.id}: {str(e)}")
            try:
                db.rollback()
            except:
                pass
            raise
    
    async def _process_calendar_event(self, event: Dict[str, Any], user: User, db: Session) -> Optional[Dict[str, Any]]:
        """Process a single calendar event and create/update meeting if needed"""
        try:
            event_id = event.get('id')
            if not event_id:
                return None
            
            # Check if we already have this calendar event
            existing_cal_event = db.query(CalendarEvent).filter(
                CalendarEvent.user_id == user.id,
                CalendarEvent.event_id == event_id
            ).first()
            
            # Extract event details
            summary = event.get('summary', 'Untitled Meeting')
            start = event.get('start', {})
            end = event.get('end', {})
            
            # Parse start and end times
            start_time = None
            end_time = None
            
            if 'dateTime' in start:
                start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            elif 'date' in start:
                # All-day event
                start_time = datetime.fromisoformat(start['date'] + 'T09:00:00+00:00')
                
            if 'dateTime' in end:
                end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
            elif 'date' in end:
                # All-day event
                end_time = datetime.fromisoformat(end['date'] + 'T17:00:00+00:00')
            
            if not start_time:
                logger.warning(f"No start time found for event {event_id}")
                return None
            
            # Extract meeting URL and determine platform
            meeting_url = None
            platform = MeetingPlatform.OTHER
            
            # Check for meeting links in various places
            location = event.get('location', '')
            description = event.get('description', '')
            hangout_link = event.get('hangoutLink', '')
            
            logger.debug(f"Event {event_id} - location: {location}")
            logger.debug(f"Event {event_id} - description: {description}")
            logger.debug(f"Event {event_id} - hangout_link: {hangout_link}")
            
            # Priority: hangoutLink > location > description
            if hangout_link:
                meeting_url = hangout_link
                platform = MeetingPlatform.GOOGLE_MEET
                logger.info(f"Using hangout link for event {event_id}: {meeting_url}")
            elif location:
                url_result = self._extract_meeting_url(location)
                if url_result:
                    meeting_url, platform = url_result
                    logger.info(f"Found meeting URL in location for event {event_id}: {meeting_url}")
            elif description:
                url_result = self._extract_meeting_url(description)
                if url_result:
                    meeting_url, platform = url_result
                    logger.info(f"Found meeting URL in description for event {event_id}: {meeting_url}")
            
            # Get participants
            attendees = event.get('attendees', [])
            participants = [attendee.get('email') for attendee in attendees if attendee.get('email')]
            
            # Calculate duration
            duration_minutes = 60  # Default
            if end_time and start_time:
                duration_minutes = int((end_time - start_time).total_seconds() / 60)
            
            # Update or create calendar event record
            if existing_cal_event:
                existing_cal_event.summary = summary
                existing_cal_event.start_time = start_time
                existing_cal_event.end_time = end_time
                existing_cal_event.meeting_url = meeting_url
                existing_cal_event.participants = participants
            else:
                existing_cal_event = CalendarEvent(
                    user_id=user.id,
                    event_id=event_id,
                    summary=summary,
                    start_time=start_time,
                    end_time=end_time,
                    meeting_url=meeting_url,
                    participants=participants
                )
                db.add(existing_cal_event)
            
            # Only create meeting if there's a meeting URL
            if meeting_url:
                logger.info(f"Creating meeting for event {event_id}: {summary} with URL: {meeting_url} and platform: {platform}")
                
                # Check if we already have a meeting for this calendar event
                existing_meeting = db.query(Meeting).filter(
                    Meeting.user_id == user.id,
                    Meeting.calendar_event_id == event_id
                ).first()
                
                try:
                    if existing_meeting:
                        # Update existing meeting
                        existing_meeting.title = summary
                        existing_meeting.scheduled_time = start_time
                        existing_meeting.start_time = start_time  # Legacy field
                        existing_meeting.end_time = end_time      # Legacy field
                        existing_meeting.duration_minutes = duration_minutes
                        existing_meeting.meeting_url = meeting_url
                        existing_meeting.platform = platform.value
                        existing_meeting.participants = participants
                        existing_meeting.updated_at = datetime.utcnow()
                        logger.info(f"Updated existing meeting {existing_meeting.id} for event {event_id}")
                    else:
                        # Create new meeting
                        # Enable auto-join if user has backend tasks enabled
                        auto_join_enabled = user.enable_backend_tasks if user.enable_backend_tasks is not None else True
                        digital_twin_id = user.id if auto_join_enabled else None
                        
                        new_meeting = Meeting(
                            user_id=user.id,
                            title=summary,
                            description=description,
                            meeting_url=meeting_url,
                            platform=platform.value,
                            scheduled_time=start_time,
                            start_time=start_time,  # Legacy field - required by DB
                            end_time=end_time,      # Legacy field
                            duration_minutes=duration_minutes,
                            status="scheduled",
                            participants=participants,
                            calendar_event_id=event_id,
                            auto_join=auto_join_enabled,  # Enable auto-join based on user preference
                            digital_twin_id=digital_twin_id,  # Set to user_id if auto-join enabled
                            created_at=datetime.utcnow()
                        )
                        db.add(new_meeting)
                        existing_meeting = new_meeting
                        logger.info(f"Created new meeting for event {event_id}")
                        
                except Exception as meeting_error:
                    logger.error(f"Error creating/updating meeting for event {event_id}: {meeting_error}")
                    # Don't fail the entire process, just skip this meeting
                    existing_meeting = None
                
                logger.info(f"Processed calendar event {event_id} -> meeting for user {user.id}")
                
                if existing_meeting:
                    return {
                        'event_id': event_id,
                        'meeting_id': existing_meeting.id if hasattr(existing_meeting, 'id') else None,
                        'title': summary,
                        'start_time': start_time.isoformat() if start_time else None,
                        'meeting_url': meeting_url,
                        'platform': platform.value,
                        'created_meeting': True
                    }
                else:
                    logger.warning(f"Failed to create meeting for event {event_id}")
                    return {
                        'event_id': event_id,
                        'title': summary,
                        'start_time': start_time.isoformat() if start_time else None,
                        'meeting_url': meeting_url,
                        'platform': platform.value,
                        'created_meeting': False,
                        'error': 'Failed to create meeting'
                    }
            else:
                # Return info about calendar event even without meeting URL
                logger.info(f"Processed calendar event {event_id} (no meeting URL) for user {user.id}")
                return {
                    'event_id': event_id,
                    'title': summary,
                    'start_time': start_time.isoformat() if start_time else None,
                    'meeting_url': None,
                    'platform': None,
                    'created_meeting': False
                }
            
        except Exception as e:
            logger.error(f"Error processing calendar event {event.get('id')}: {e}")
            return None
    
    def _extract_meeting_url(self, text: str) -> Optional[tuple[str, MeetingPlatform]]:
        """Extract meeting URL and platform from text"""
        if not text:
            return None
            
        logger.debug(f"Extracting meeting URL from text: {text}")
        text_lower = text.lower()
        
        # Check for different meeting platforms
        if 'zoom.us' in text_lower:
            # Extract Zoom URL
            import re
            zoom_pattern = r'https?://[^\s]*zoom\.us[^\s]*'
            match = re.search(zoom_pattern, text, re.IGNORECASE)
            if match:
                url = match.group()
                logger.info(f"Found Zoom URL: {url}")
                return url, MeetingPlatform.ZOOM
                
        elif 'meet.google.com' in text_lower:
            # Extract Google Meet URL
            import re
            meet_pattern = r'https?://meet\.google\.com/[^\s]*'
            match = re.search(meet_pattern, text, re.IGNORECASE)
            if match:
                url = match.group()
                logger.info(f"Found Google Meet URL: {url}")
                return url, MeetingPlatform.GOOGLE_MEET
                
        elif 'teams.microsoft.com' in text_lower or 'teams.live.com' in text_lower:
            # Extract Teams URL
            import re
            teams_pattern = r'https?://[^\s]*teams\.(microsoft|live)\.com[^\s]*'
            match = re.search(teams_pattern, text, re.IGNORECASE)
            if match:
                url = match.group()
                logger.info(f"Found Teams URL: {url}")
                return url, MeetingPlatform.MICROSOFT_TEAMS
                
        elif 'webex.com' in text_lower:
            # Extract Webex URL
            import re
            webex_pattern = r'https?://[^\s]*webex\.com[^\s]*'
            match = re.search(webex_pattern, text, re.IGNORECASE)
            if match:
                url = match.group()
                logger.info(f"Found Webex URL: {url}")
                return url, MeetingPlatform.WEBEX
        
        # Check for any HTTP URL as a fallback
        import re
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, text, re.IGNORECASE)
        if match:
            url = match.group()
            logger.info(f"Found generic URL: {url}")
            return url, MeetingPlatform.OTHER
        
        logger.debug(f"No meeting URL found in text: {text}")
        return None


# Initialize the service
calendar_service = GoogleCalendarService()
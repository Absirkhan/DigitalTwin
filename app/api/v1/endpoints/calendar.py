"""
Calendar webhook endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.core.database import get_db
from app.services.auth import get_current_user_bearer
from app.services.calendar import calendar_service
from app.services.webhook_auto_setup import webhook_auto_setup
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook")
async def calendar_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Google Calendar webhook notifications
    This endpoint receives notifications when calendar events change
    """
    try:
        # Get headers (convert to lowercase for case-insensitive lookup)
        headers = dict(request.headers)
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        # Log the webhook for debugging
        logger.info(f"Received calendar webhook from {request.client.host if request.client else 'unknown'}")
        logger.info(f"Headers: {headers}")
        
        # Extract required headers (case-insensitive)
        resource_id = headers_lower.get('x-goog-resource-id')
        resource_state = headers_lower.get('x-goog-resource-state') 
        channel_token = headers_lower.get('x-goog-channel-token')
        channel_id = headers_lower.get('x-goog-channel-id')
        
        logger.info(f"Webhook data - Resource ID: {resource_id}, State: {resource_state}, Token: {channel_token}, Channel: {channel_id}")
        
        # Extract user ID from token
        if not channel_token:
            logger.warning("No channel token in webhook headers")
            return {"status": "ignored", "reason": "no token"}
        
        try:
            user_id = int(channel_token)
        except ValueError:
            logger.warning(f"Invalid channel token: {channel_token}")
            return {"status": "ignored", "reason": "invalid token"}
        
        # Process the notification
        success = await calendar_service.handle_calendar_notification(
            headers, user_id, db
        )
        
        if success:
            return {"status": "success"}
        else:
            return {"status": "failed"}
            
    except Exception as e:
        logger.error(f"Error processing calendar webhook: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/setup-webhook")
async def setup_calendar_webhook(
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    Set up Google Calendar webhook for the current user
    This needs to be called to start receiving calendar notifications
    """
    try:
        result = await calendar_service.setup_calendar_webhook(current_user, db)
        return {
            "message": "Calendar webhook set up successfully",
            "webhook_info": result
        }
    except Exception as e:
        logger.error(f"Error setting up calendar webhook for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set up calendar webhook: {str(e)}"
        )


@router.delete("/webhook")
async def stop_calendar_webhook(
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    Stop Google Calendar webhook for the current user
    """
    try:
        success = await calendar_service.stop_calendar_webhook(current_user, db)
        if success:
            return {"message": "Calendar webhook stopped successfully"}
        else:
            return {"message": "No active webhook found or failed to stop"}
    except Exception as e:
        logger.error(f"Error stopping calendar webhook for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop calendar webhook: {str(e)}"
        )


@router.post("/sync")
async def sync_calendar_events(
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    Manually sync calendar events for the current user
    This will fetch recent calendar events and create/update meetings
    """
    try:
        result = await calendar_service.sync_user_calendar_events(current_user, db)
        return {
            "message": f"Successfully synced {result['total_events_processed']} calendar events, created {result['meetings_created']} meetings",
            "summary": {
                "total_events_processed": result['total_events_processed'],
                "meetings_created": result['meetings_created'],
                "events_with_meeting_urls": len(result['meetings_with_urls'])
            },
            "events": result['events'],
            "meetings": result['meetings_with_urls']
        }
    except Exception as e:
        logger.error(f"Error syncing calendar events for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync calendar events: {str(e)}"
        )


@router.get("/webhook-status")
async def get_webhook_status(
    current_user: User = Depends(get_current_user_bearer)
):
    """
    Get the current webhook status for the user
    """
    try:
        if not current_user.oauth_tokens or 'calendar_webhook' not in current_user.oauth_tokens:
            return {
                "webhook_active": False,
                "message": "No webhook configured"
            }
        
        webhook_info = current_user.oauth_tokens['calendar_webhook']
        return {
            "webhook_active": True,
            "channel_id": webhook_info.get('channel_id'),
            "expiration": webhook_info.get('expiration'),
            "created_at": webhook_info.get('created_at')
        }
    except Exception as e:
        logger.error(f"Error getting webhook status for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get webhook status: {str(e)}"
        )


@router.post("/demo-setup")
async def setup_demo_environment(
    current_user: User = Depends(get_current_user_bearer),
    db: Session = Depends(get_db)
):
    """
    One-click demo setup: automatically configure ngrok and webhook
    Perfect for demonstrations and testing
    """
    try:
        # Auto-setup ngrok and webhook URL
        setup_result = await webhook_auto_setup.auto_setup_for_demo()
        
        if setup_result["status"] == "ready":
            # Try to setup webhook with Google
            try:
                webhook_result = await calendar_service.setup_calendar_webhook(current_user, db)
                return {
                    "demo_ready": True,
                    "message": "Demo environment ready! Calendar webhooks are active.",
                    "webhook_url": setup_result["webhook_url"],
                    "webhook_info": webhook_result,
                    "instructions": [
                        "✅ Ngrok tunnel is active",
                        "✅ Webhook registered with Google Calendar",
                        "✅ Ready for demo - add calendar events and see them sync automatically!"
                    ]
                }
            except Exception as webhook_error:
                return {
                    "demo_ready": False,
                    "message": "Ngrok ready but webhook setup failed",
                    "webhook_url": setup_result["webhook_url"],
                    "error": str(webhook_error),
                    "instructions": [
                        "✅ Ngrok tunnel is active",
                        "❌ Webhook setup failed - you can try the manual setup",
                        f"Webhook URL: {setup_result['webhook_url']}/api/v1/calendar/webhook"
                    ]
                }
        else:
            return {
                "demo_ready": False,
                "message": setup_result["message"],
                "instructions": setup_result.get("instructions", [])
            }
            
    except Exception as e:
        logger.error(f"Error setting up demo environment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup demo environment: {str(e)}"
        )
"""
WebSocket Connection Manager for Real-Time Transcript Streaming

Ultra-low latency design:
- Direct WebSocket send (no queuing)
- Per-meeting connection pools
- Efficient broadcast to multiple clients
- Automatic cleanup on disconnect
"""

import asyncio
import logging
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from app.services.redis_pubsub import get_redis_pubsub

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """
    Manages WebSocket connections for real-time transcript streaming.

    **Performance optimizations:**
    - O(1) connection lookup by meeting ID
    - Parallel broadcast to all clients
    - Automatic Redis subscription management
    - No message buffering (direct streaming)
    """

    def __init__(self):
        # Structure: {meeting_id: {websocket_1, websocket_2, ...}}
        self.active_connections: Dict[int, Set[WebSocket]] = {}

        # Track which meetings have active Redis subscriptions
        self._subscribed_meetings: Set[int] = set()

        # Redis pub/sub service
        self.redis_pubsub = get_redis_pubsub()

    async def connect(self, websocket: WebSocket, meeting_id: int, user_id: int):
        """
        Register a new WebSocket connection for a meeting.

        **Low-latency connection setup:**
        1. Add to connection pool (WebSocket already accepted by endpoint)
        2. Subscribe to Redis channel (if first connection)
        3. Send confirmation message

        Args:
            websocket: FastAPI WebSocket instance (must already be accepted)
            meeting_id: Meeting to stream
            user_id: Authenticated user ID
        """
        # Note: WebSocket is already accepted by the endpoint before calling this
        # This allows authentication to happen before registration

        # Add to connection pool
        if meeting_id not in self.active_connections:
            self.active_connections[meeting_id] = set()

        self.active_connections[meeting_id].add(websocket)

        connection_count = len(self.active_connections[meeting_id])
        logger.info(
            f"✅ WebSocket connected: meeting={meeting_id}, user={user_id}, "
            f"total_connections={connection_count}"
        )

        # Subscribe to Redis channel if this is the first connection
        if meeting_id not in self._subscribed_meetings:
            await self._subscribe_to_meeting(meeting_id)

        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "meeting_id": meeting_id,
            "message": "Connected to real-time transcript stream"
        })

    async def disconnect(self, websocket: WebSocket, meeting_id: int):
        """
        Remove a WebSocket connection and cleanup resources.

        Args:
            websocket: WebSocket to disconnect
            meeting_id: Meeting ID
        """
        if meeting_id in self.active_connections:
            self.active_connections[meeting_id].discard(websocket)

            remaining = len(self.active_connections[meeting_id])
            logger.info(
                f"❌ WebSocket disconnected: meeting={meeting_id}, "
                f"remaining_connections={remaining}"
            )

            # If no more connections, unsubscribe from Redis
            if remaining == 0:
                del self.active_connections[meeting_id]
                await self._unsubscribe_from_meeting(meeting_id)

    async def broadcast_to_meeting(
        self,
        meeting_id: int,
        message: dict
    ):
        """
        Broadcast a message to all connected clients for a meeting.

        **Speed optimization:**
        - Parallel send to all clients (asyncio.gather)
        - Remove dead connections automatically
        - No waiting for slow clients

        Args:
            meeting_id: Target meeting
            message: JSON-serializable message
        """
        if meeting_id not in self.active_connections:
            return

        connections = self.active_connections[meeting_id].copy()
        dead_connections = []

        # Broadcast to all clients in parallel
        async def send_to_client(ws: WebSocket):
            try:
                await ws.send_json(message)
                print(f"   ✅ Sent to WebSocket client successfully")
            except WebSocketDisconnect:
                print(f"   ❌ WebSocket disconnected during send")
                dead_connections.append(ws)
            except Exception as e:
                print(f"   ❌ Error sending to WebSocket: {e}")
                logger.error(f"Error sending to WebSocket: {e}")
                dead_connections.append(ws)

        # Send to all clients concurrently (no blocking)
        await asyncio.gather(
            *[send_to_client(ws) for ws in connections],
            return_exceptions=True
        )

        # Cleanup dead connections
        for ws in dead_connections:
            await self.disconnect(ws, meeting_id)

    async def send_personal_message(
        self,
        websocket: WebSocket,
        message: dict
    ):
        """
        Send a message to a specific WebSocket connection.

        Args:
            websocket: Target connection
            message: JSON message
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")

    async def _subscribe_to_meeting(self, meeting_id: int):
        """
        Subscribe to Redis pub/sub channel for a meeting.

        Creates a background task that forwards Redis messages to WebSocket clients.
        """
        async def message_handler(data: dict):
            """Forward Redis messages to all connected WebSocket clients"""
            print(f"\n📨 WEBSOCKET MANAGER RECEIVED MESSAGE FROM REDIS")
            print(f"   Meeting ID: {meeting_id}")
            print(f"   Message Type: {data.get('type')}")
            print(f"   Data: {data}")
            print(f"   Broadcasting to {self.get_connection_count(meeting_id)} client(s)\n")

            await self.broadcast_to_meeting(meeting_id, data)

            print(f"✅ Broadcast complete for meeting {meeting_id}\n")

        await self.redis_pubsub.subscribe_to_meeting(meeting_id, message_handler)
        self._subscribed_meetings.add(meeting_id)

        logger.info(f"🎧 Subscribed to Redis channel for meeting {meeting_id}")

    async def _unsubscribe_from_meeting(self, meeting_id: int):
        """
        Unsubscribe from Redis channel when no clients are connected.
        """
        await self.redis_pubsub.unsubscribe_from_meeting(meeting_id)
        self._subscribed_meetings.discard(meeting_id)

        logger.info(f"🔇 Unsubscribed from Redis channel for meeting {meeting_id}")

    def get_connection_count(self, meeting_id: int) -> int:
        """Get number of active WebSocket connections for a meeting"""
        return len(self.active_connections.get(meeting_id, set()))

    def get_all_active_meetings(self) -> Set[int]:
        """Get all meeting IDs with active connections"""
        return set(self.active_connections.keys())

    async def send_meeting_status(self, meeting_id: int, status: str):
        """
        Broadcast meeting status change to all connected clients.

        Args:
            meeting_id: Meeting ID
            status: New status (e.g., "in_progress", "completed")
        """
        await self.broadcast_to_meeting(meeting_id, {
            "type": "meeting_status",
            "meeting_id": meeting_id,
            "status": status
        })

    async def cleanup_all_connections(self):
        """
        Cleanup all connections (called on server shutdown).
        """
        logger.info("🧹 Cleaning up all WebSocket connections...")

        for meeting_id in list(self.active_connections.keys()):
            connections = self.active_connections[meeting_id].copy()

            for ws in connections:
                try:
                    await ws.close(code=1001, reason="Server shutdown")
                except Exception:
                    pass

            await self._unsubscribe_from_meeting(meeting_id)

        self.active_connections.clear()
        self._subscribed_meetings.clear()

        logger.info("✅ All WebSocket connections closed")


# Global singleton instance
_manager_instance: Optional[WebSocketConnectionManager] = None


def get_websocket_manager() -> WebSocketConnectionManager:
    """
    Get the global WebSocket connection manager.

    Returns:
        WebSocketConnectionManager: Singleton instance
    """
    global _manager_instance

    if _manager_instance is None:
        _manager_instance = WebSocketConnectionManager()

    return _manager_instance

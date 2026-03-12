"""
Redis Pub/Sub Service for Real-Time Transcript Broadcasting

Optimized for low-latency message delivery with:
- Async Redis operations
- Direct pub/sub (no intermediate queuing)
- Connection pooling
- Efficient JSON serialization
"""

import json
import asyncio
import logging
from typing import Dict, Any, Callable, Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisPubSubService:
    """
    High-performance Redis pub/sub service for real-time transcript streaming.

    Design for minimal latency:
    - Single Redis connection pool shared across all operations
    - Fire-and-forget publish (non-blocking)
    - Binary-safe message encoding
    - No message persistence (real-time only)
    """

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self._subscriber_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self):
        """Initialize Redis connection pool"""
        if self.redis is None:
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,  # Handle multiple concurrent connections
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            logger.info("✅ Redis pub/sub service connected")

    async def disconnect(self):
        """Close Redis connections"""
        # Cancel all subscriber tasks
        for task in self._subscriber_tasks.values():
            task.cancel()
        self._subscriber_tasks.clear()

        if self.pubsub:
            await self.pubsub.close()

        if self.redis:
            await self.redis.close()
            logger.info("❌ Redis pub/sub service disconnected")

    def _get_channel_name(self, meeting_id: int) -> str:
        """Generate channel name for a meeting"""
        return f"meeting:{meeting_id}:transcript"

    async def publish_transcript_chunk(
        self,
        meeting_id: int,
        chunk_data: Dict[str, Any]
    ) -> None:
        """
        Publish a transcript chunk to the meeting's channel.

        **Optimized for speed:**
        - No awaiting publish result (fire-and-forget)
        - Pre-serialized JSON
        - Direct Redis PUBLISH command

        Args:
            meeting_id: Meeting identifier
            chunk_data: Transcript chunk containing speaker, text, timestamp
        """
        if self.redis is None:
            await self.connect()

        channel = self._get_channel_name(meeting_id)

        # Add message type for frontend routing
        message = {
            "type": "transcript_chunk",
            "meeting_id": meeting_id,
            **chunk_data
        }

        try:
            # Fire-and-forget publish - minimal latency
            subscribers = await self.redis.publish(
                channel,
                json.dumps(message, separators=(',', ':'))  # Compact JSON
            )

            print(f"\n📤 REDIS PUBLISH")
            print(f"   Channel: {channel}")
            print(f"   Subscribers: {subscribers}")
            print(f"   Message: {json.dumps(message, indent=2)}")
            print(f"   Text: {chunk_data.get('text', '')[:100]}...\n")

            logger.info(
                f"📤 Published chunk to {channel} ({subscribers} subscribers): "
                f"{chunk_data.get('text', '')[:50]}..."
            )

        except Exception as e:
            logger.error(f"❌ Failed to publish to {channel}: {e}")

    async def subscribe_to_meeting(
        self,
        meeting_id: int,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Subscribe to a meeting's transcript channel.

        **Low-latency subscription:**
        - Dedicated pub/sub connection per meeting
        - Async message processing
        - No message buffering

        Args:
            meeting_id: Meeting to subscribe to
            callback: Async function to call with each message
        """
        if self.redis is None:
            await self.connect()

        channel = self._get_channel_name(meeting_id)

        # Create dedicated pub/sub connection
        pubsub = self.redis.pubsub()

        async def _subscribe_loop():
            """Background task that listens for messages"""
            try:
                await pubsub.subscribe(channel)
                logger.info(f"🎧 Subscribed to {channel}")

                async for message in pubsub.listen():
                    # Skip subscription confirmation messages
                    if message["type"] != "message":
                        continue

                    try:
                        # Parse and forward to callback
                        data = json.loads(message["data"])
                        await callback(data)

                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in message: {e}")
                    except Exception as e:
                        logger.error(f"Error in message callback: {e}")

            except asyncio.CancelledError:
                logger.info(f"🛑 Unsubscribing from {channel}")
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception as e:
                logger.error(f"❌ Subscription error for {channel}: {e}")

        # Start background subscription task
        task_key = f"{meeting_id}"
        if task_key in self._subscriber_tasks:
            self._subscriber_tasks[task_key].cancel()

        task = asyncio.create_task(_subscribe_loop())
        self._subscriber_tasks[task_key] = task

    async def unsubscribe_from_meeting(self, meeting_id: int) -> None:
        """Stop listening to a meeting's channel"""
        task_key = f"{meeting_id}"

        if task_key in self._subscriber_tasks:
            self._subscriber_tasks[task_key].cancel()
            del self._subscriber_tasks[task_key]
            logger.info(f"🔇 Unsubscribed from meeting {meeting_id}")

    async def publish_meeting_event(
        self,
        meeting_id: int,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Publish non-transcript events (e.g., meeting_started, meeting_ended).

        Args:
            meeting_id: Meeting identifier
            event_type: Event type (e.g., "meeting_started", "meeting_ended")
            data: Event payload
        """
        if self.redis is None:
            await self.connect()

        channel = self._get_channel_name(meeting_id)

        message = {
            "type": event_type,
            "meeting_id": meeting_id,
            **data
        }

        try:
            await self.redis.publish(channel, json.dumps(message))
            logger.info(f"📢 Published {event_type} event to meeting {meeting_id}")
        except Exception as e:
            logger.error(f"❌ Failed to publish event: {e}")

    async def get_active_subscribers(self, meeting_id: int) -> int:
        """Get number of active subscribers to a meeting's channel"""
        if self.redis is None:
            await self.connect()

        channel = self._get_channel_name(meeting_id)

        try:
            # PUBSUB NUMSUB returns number of subscribers
            result = await self.redis.execute_command(
                "PUBSUB", "NUMSUB", channel
            )
            # Result format: [channel_name, subscriber_count]
            return result[1] if len(result) > 1 else 0
        except Exception as e:
            logger.error(f"❌ Failed to get subscriber count: {e}")
            return 0


# Global singleton instance
_redis_pubsub_instance: Optional[RedisPubSubService] = None


def get_redis_pubsub() -> RedisPubSubService:
    """
    Get the global Redis pub/sub service instance.

    Returns:
        RedisPubSubService: Singleton instance
    """
    global _redis_pubsub_instance

    if _redis_pubsub_instance is None:
        _redis_pubsub_instance = RedisPubSubService()

    return _redis_pubsub_instance


async def init_redis_pubsub():
    """Initialize Redis pub/sub on application startup"""
    service = get_redis_pubsub()
    await service.connect()
    return service


async def shutdown_redis_pubsub():
    """Cleanup Redis pub/sub on application shutdown"""
    global _redis_pubsub_instance

    if _redis_pubsub_instance:
        await _redis_pubsub_instance.disconnect()
        _redis_pubsub_instance = None

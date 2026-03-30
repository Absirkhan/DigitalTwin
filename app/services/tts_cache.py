"""
TTS Response Caching Service

Provides Redis-based caching for synthesized speech to dramatically reduce latency
for repeated requests. Cache key = hash(user_id + text).

Benefits:
- Instant response for cached phrases (<50ms vs 2-3s)
- Reduces CPU load on TTS model
- Common phrases (greetings, acknowledgments) = instant

Cache Configuration:
- TTL: 24 hours (86400 seconds)
- Max entries per user: Auto-managed by Redis LRU
- Storage: ~50KB per 10-second audio clip
"""

import hashlib
import logging
from typing import Optional
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class TTSCacheService:
    """
    Singleton service for caching TTS responses in Redis.
    """

    _instance: Optional['TTSCacheService'] = None
    _redis_client: Optional[redis.Redis] = None

    # Cache configuration
    CACHE_TTL = 86400  # 24 hours
    CACHE_PREFIX = "tts:audio:"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize cache service."""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            logger.info("TTS cache service initialized")

    async def _get_redis(self) -> redis.Redis:
        """
        Get or create Redis connection.

        For Celery tasks that create new event loops, we need to create a new
        Redis client for each event loop to avoid "Event loop is closed" errors.

        Returns:
            Redis client instance
        """
        try:
            import asyncio
            current_loop = asyncio.get_event_loop()

            # Check if we have a client and if it's associated with the current loop
            if self._redis_client is not None:
                try:
                    # Try to ping to verify connection is still valid
                    await self._redis_client.ping()
                    return self._redis_client
                except Exception:
                    # Connection is invalid or tied to closed loop
                    logger.debug("Existing Redis connection invalid, creating new one")
                    try:
                        await self._redis_client.close()
                    except Exception:
                        pass
                    self._redis_client = None

            # Create new Redis connection
            self._redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False  # Keep binary data as bytes
            )
            # Test connection
            await self._redis_client.ping()
            logger.info("TTS cache connected to Redis")
            return self._redis_client

        except Exception as e:
            logger.error(f"Failed to connect to Redis for TTS cache: {e}")
            raise

    def _generate_cache_key(self, user_id: str, text: str) -> str:
        """
        Generate cache key from user_id and text.

        Args:
            user_id: User identifier
            text: Text to synthesize

        Returns:
            Cache key string (e.g., "tts:audio:user123:abc123def456...")
        """
        # Normalize text (lowercase, strip whitespace)
        normalized_text = text.strip().lower()

        # Generate hash of text (MD5 is fast enough for cache keys)
        text_hash = hashlib.md5(normalized_text.encode('utf-8')).hexdigest()

        return f"{self.CACHE_PREFIX}{user_id}:{text_hash}"

    async def get(self, user_id: str, text: str) -> Optional[bytes]:
        """
        Get cached audio from Redis.

        Args:
            user_id: User identifier
            text: Text that was synthesized

        Returns:
            Audio data as bytes if cached, None otherwise
        """
        try:
            redis_client = await self._get_redis()
            cache_key = self._generate_cache_key(user_id, text)

            audio_data = await redis_client.get(cache_key)

            if audio_data:
                logger.info(f"TTS cache HIT for user {user_id} (key: {cache_key})")
                return audio_data
            else:
                logger.info(f"TTS cache MISS for user {user_id} (key: {cache_key})")
                return None

        except Exception as e:
            logger.error(f"TTS cache get failed: {e}")
            return None  # Fail gracefully, don't block synthesis

    async def set(self, user_id: str, text: str, audio_data: bytes) -> bool:
        """
        Store synthesized audio in Redis cache.

        Args:
            user_id: User identifier
            text: Text that was synthesized
            audio_data: Audio data as bytes (WAV format)

        Returns:
            True if cached successfully, False otherwise
        """
        try:
            redis_client = await self._get_redis()
            cache_key = self._generate_cache_key(user_id, text)

            # Store with TTL
            await redis_client.setex(
                cache_key,
                self.CACHE_TTL,
                audio_data
            )

            logger.info(f"TTS cache SET for user {user_id} (key: {cache_key}, size: {len(audio_data)} bytes)")
            return True

        except Exception as e:
            logger.error(f"TTS cache set failed: {e}")
            return False  # Fail gracefully

    async def delete(self, user_id: str, text: str) -> bool:
        """
        Delete cached audio from Redis.

        Args:
            user_id: User identifier
            text: Text to remove from cache

        Returns:
            True if deleted, False otherwise
        """
        try:
            redis_client = await self._get_redis()
            cache_key = self._generate_cache_key(user_id, text)

            result = await redis_client.delete(cache_key)

            if result > 0:
                logger.info(f"TTS cache DELETE for user {user_id} (key: {cache_key})")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"TTS cache delete failed: {e}")
            return False

    async def clear_user_cache(self, user_id: str) -> int:
        """
        Clear all cached audio for a specific user.

        Args:
            user_id: User identifier

        Returns:
            Number of keys deleted
        """
        try:
            redis_client = await self._get_redis()
            pattern = f"{self.CACHE_PREFIX}{user_id}:*"

            # Find all keys matching pattern
            keys = []
            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)

            # Delete all found keys
            if keys:
                deleted = await redis_client.delete(*keys)
                logger.info(f"TTS cache cleared {deleted} entries for user {user_id}")
                return deleted
            else:
                return 0

        except Exception as e:
            logger.error(f"TTS cache clear failed: {e}")
            return 0

    async def get_cache_stats(self, user_id: str) -> dict:
        """
        Get cache statistics for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with cache stats (count, total_size)
        """
        try:
            redis_client = await self._get_redis()
            pattern = f"{self.CACHE_PREFIX}{user_id}:*"

            count = 0
            total_size = 0

            async for key in redis_client.scan_iter(match=pattern):
                count += 1
                # Get size of this cached audio
                data = await redis_client.get(key)
                if data:
                    total_size += len(data)

            return {
                "user_id": user_id,
                "cached_entries": count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }

        except Exception as e:
            logger.error(f"TTS cache stats failed: {e}")
            return {"error": str(e)}

    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            logger.info("TTS cache Redis connection closed")


# Singleton instance
tts_cache_service = TTSCacheService()

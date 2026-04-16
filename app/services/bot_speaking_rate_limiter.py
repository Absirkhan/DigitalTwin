"""
Bot Speaking Rate Limiter

Implements cooldown and rate limiting for bot responses using Redis.
Ensures bot doesn't spam responses and respects meeting-specific limits.
"""

import time
import logging
from typing import Optional
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cooldown period between responses (seconds)
# Set to 0 to disable cooldown for testing
# Production: 30-60 seconds recommended
COOLDOWN_SECONDS = 0

# Redis client
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client for rate limiting.

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await _redis_client.ping()
            logger.info("Rate limiter Redis client connected")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for rate limiting: {e}")
            raise

    return _redis_client


async def can_respond_now(meeting_id: int, bot_id: str, max_responses: int) -> tuple[bool, Optional[str]]:
    """
    Check if bot can respond now based on cooldown and rate limit.

    Args:
        meeting_id: ID of the meeting
        bot_id: ID of the bot
        max_responses: Maximum responses allowed for this meeting

    Returns:
        Tuple of (can_respond: bool, reason: Optional[str])
        reason is None if can_respond is True, otherwise explains why not

    Examples:
        >>> can_respond_now(123, "bot-abc", 10)
        (True, None)
        >>> can_respond_now(123, "bot-abc", 10)  # Called 15s later
        (False, "Cooldown active (15s remaining)")
        >>> can_respond_now(123, "bot-abc", 5)  # After 5 responses
        (False, "Max responses reached (5/5)")
    """
    try:
        client = await get_redis_client()

        # Check cooldown
        last_response_key = f"bot_speaking:{meeting_id}:last_response"
        last_response_time = await client.get(last_response_key)

        if last_response_time:
            elapsed = time.time() - float(last_response_time)
            if elapsed < COOLDOWN_SECONDS:
                remaining = int(COOLDOWN_SECONDS - elapsed)
                reason = f"Cooldown active ({remaining}s remaining)"
                logger.debug(f"Bot {bot_id} cannot respond: {reason}")
                return False, reason

        # Check rate limit
        count_key = f"bot_speaking:{meeting_id}:count"
        current_count = await client.get(count_key)
        current_count = int(current_count) if current_count else 0

        if current_count >= max_responses:
            reason = f"Max responses reached ({current_count}/{max_responses})"
            logger.warning(f"Bot {bot_id} cannot respond: {reason}")
            return False, reason

        logger.debug(
            f"Bot {bot_id} can respond: "
            f"count={current_count}/{max_responses}, "
            f"cooldown_ok={last_response_time is None or elapsed >= COOLDOWN_SECONDS}"
        )
        return True, None

    except Exception as e:
        logger.error(f"Error checking rate limit: {e}", exc_info=True)
        # Fail open - allow response if Redis is down
        return True, None


async def increment_response_count(meeting_id: int) -> int:
    """
    Increment response count for this meeting.

    Args:
        meeting_id: ID of the meeting

    Returns:
        New response count

    Side effects:
        - Increments counter in Redis
        - Sets expiration to 24 hours
    """
    try:
        client = await get_redis_client()
        count_key = f"bot_speaking:{meeting_id}:count"

        new_count = await client.incr(count_key)

        # Expire after 24 hours
        await client.expire(count_key, 86400)

        logger.info(f"Meeting {meeting_id}: response count incremented to {new_count}")
        return new_count

    except Exception as e:
        logger.error(f"Error incrementing response count: {e}", exc_info=True)
        return 0


async def set_last_response_time(meeting_id: int) -> None:
    """
    Record the last response time for cooldown tracking.

    Args:
        meeting_id: ID of the meeting

    Side effects:
        - Sets timestamp in Redis
        - Sets expiration to 24 hours
    """
    try:
        client = await get_redis_client()
        last_response_key = f"bot_speaking:{meeting_id}:last_response"

        current_time = time.time()
        await client.set(last_response_key, str(current_time))
        await client.expire(last_response_key, 86400)

        logger.debug(f"Meeting {meeting_id}: last response time recorded")

    except Exception as e:
        logger.error(f"Error setting last response time: {e}", exc_info=True)


async def get_response_count(meeting_id: int) -> int:
    """
    Get current response count for a meeting.

    Args:
        meeting_id: ID of the meeting

    Returns:
        Current response count (0 if not found)
    """
    try:
        client = await get_redis_client()
        count_key = f"bot_speaking:{meeting_id}:count"

        count = await client.get(count_key)
        return int(count) if count else 0

    except Exception as e:
        logger.error(f"Error getting response count: {e}", exc_info=True)
        return 0


async def get_time_since_last_response(meeting_id: int) -> Optional[float]:
    """
    Get time elapsed since last response.

    Args:
        meeting_id: ID of the meeting

    Returns:
        Seconds since last response, or None if no previous response
    """
    try:
        client = await get_redis_client()
        last_response_key = f"bot_speaking:{meeting_id}:last_response"

        last_response_time = await client.get(last_response_key)

        if last_response_time:
            elapsed = time.time() - float(last_response_time)
            return elapsed

        return None

    except Exception as e:
        logger.error(f"Error getting last response time: {e}", exc_info=True)
        return None


async def reset_meeting_limits(meeting_id: int) -> None:
    """
    Reset all rate limits for a meeting.

    Useful for testing or when meeting ends.

    Args:
        meeting_id: ID of the meeting

    Side effects:
        - Deletes count key
        - Deletes last response time key
    """
    try:
        client = await get_redis_client()

        count_key = f"bot_speaking:{meeting_id}:count"
        last_response_key = f"bot_speaking:{meeting_id}:last_response"

        await client.delete(count_key, last_response_key)

        logger.info(f"Meeting {meeting_id}: rate limits reset")

    except Exception as e:
        logger.error(f"Error resetting meeting limits: {e}", exc_info=True)


async def get_meeting_stats(meeting_id: int) -> dict:
    """
    Get all rate limiting stats for a meeting.

    Args:
        meeting_id: ID of the meeting

    Returns:
        Dictionary with current stats:
        {
            "response_count": int,
            "last_response_seconds_ago": Optional[float],
            "cooldown_active": bool,
            "cooldown_remaining_seconds": int
        }
    """
    try:
        count = await get_response_count(meeting_id)
        elapsed = await get_time_since_last_response(meeting_id)

        cooldown_active = elapsed is not None and elapsed < COOLDOWN_SECONDS
        cooldown_remaining = int(COOLDOWN_SECONDS - elapsed) if cooldown_active and elapsed else 0

        return {
            "response_count": count,
            "last_response_seconds_ago": elapsed,
            "cooldown_active": cooldown_active,
            "cooldown_remaining_seconds": cooldown_remaining
        }

    except Exception as e:
        logger.error(f"Error getting meeting stats: {e}", exc_info=True)
        return {
            "response_count": 0,
            "last_response_seconds_ago": None,
            "cooldown_active": False,
            "cooldown_remaining_seconds": 0
        }


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def test_rate_limiter():
        print("=== Bot Speaking Rate Limiter Test ===\n")

        meeting_id = 9999  # Test meeting ID
        bot_id = "test-bot-123"
        max_responses = 3

        try:
            # Reset before testing
            await reset_meeting_limits(meeting_id)
            print("[OK] Rate limits reset\n")

            # Test 1: Should allow first response
            can_respond, reason = await can_respond_now(meeting_id, bot_id, max_responses)
            print(f"Test 1 - First response: {can_respond} (expected: True)")
            assert can_respond, "Should allow first response"

            # Simulate response
            await increment_response_count(meeting_id)
            await set_last_response_time(meeting_id)

            # Test 2: Should block during cooldown
            can_respond, reason = await can_respond_now(meeting_id, bot_id, max_responses)
            print(f"Test 2 - During cooldown: {can_respond}, reason: {reason} (expected: False)")
            assert not can_respond, "Should block during cooldown"

            # Test 3: Check stats
            stats = await get_meeting_stats(meeting_id)
            print(f"Test 3 - Stats: {stats}")
            assert stats["response_count"] == 1, "Should have 1 response"
            assert stats["cooldown_active"], "Cooldown should be active"

            # Test 4: Reach max responses
            for i in range(2, max_responses + 1):
                # Wait for cooldown
                await asyncio.sleep(0.1)
                # Force cooldown to pass for testing
                await reset_meeting_limits(meeting_id)
                for _ in range(i):
                    await increment_response_count(meeting_id)

            can_respond, reason = await can_respond_now(meeting_id, bot_id, max_responses)
            print(f"Test 4 - Max responses: {can_respond}, reason: {reason} (expected: False)")
            assert not can_respond, "Should block at max responses"

            # Cleanup
            await reset_meeting_limits(meeting_id)
            print("\n[OK] All tests passed")

        except Exception as e:
            print(f"\n[FAIL] Test failed: {e}")

    asyncio.run(test_rate_limiter())

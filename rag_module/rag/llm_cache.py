"""
LLM Response Cache - Redis-based caching for generated responses

This module provides caching for LLM-generated responses to improve latency
and reduce computational overhead. It uses Redis for fast in-memory storage
and retrieval, similar to the TTS caching pattern.

Key Features:
- Hash-based cache keys (SHA256 of full prompt)
- TTL-based expiration (24 hours default)
- Cache hit/miss statistics tracking
- Automatic cache invalidation on model changes
- Thread-safe operations

Cache Performance:
- Cache hit: <50ms (instant response)
- Cache miss: 3000-4000ms (full LLM generation)
- Expected hit rate: 30-40% for common queries

Usage:
    cache = LLMResponseCache()

    # Try to get cached response
    cached = cache.get_cached_response(prompt)
    if cached:
        return cached['response']  # <50ms

    # Generate new response
    response = llm.generate(prompt)  # 3-4s

    # Cache for future queries
    cache.cache_response(prompt, response, tokens_generated=150)
"""

import hashlib
import json
import time
from typing import Optional, Dict
from pathlib import Path
import sys

# Add parent directory to path for config import
sys.path.append(str(Path(__file__).parent.parent))

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: redis-py not installed. LLM caching will be disabled.")
    print("Install with: pip install redis")


class LLMResponseCache:
    """
    Redis-based cache for LLM-generated responses.

    The cache uses SHA256 hashes of prompts as keys to ensure consistent
    lookup while avoiding Redis key size limitations. Cache entries include
    the full response text, token count, and metadata for analytics.

    Attributes:
        redis_client: Redis connection instance (or None if unavailable)
        enabled: Whether caching is enabled
        key_prefix: Prefix for all cache keys
        ttl_seconds: Time-to-live for cache entries
        model_version: Model identifier for cache invalidation
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "llm_response:",
        ttl_seconds: int = 86400,  # 24 hours
        enabled: bool = True,
        model_version: str = "qwen2.5-0.5b-q4"
    ):
        """
        Initialize LLM response cache.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all cache keys
            ttl_seconds: Time-to-live for cache entries (seconds)
            enabled: Enable/disable caching
            model_version: Model identifier (included in cache key)
        """
        self.enabled = enabled and REDIS_AVAILABLE
        self.key_prefix = key_prefix
        self.ttl_seconds = ttl_seconds
        self.model_version = model_version

        # Initialize Redis connection
        self.redis_client = None
        if self.enabled:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                print("[OK] LLM cache initialized (Redis connected)")
            except (redis.ConnectionError, redis.TimeoutError) as e:
                print(f"[WARN] Redis unavailable, caching disabled: {e}")
                self.enabled = False
                self.redis_client = None
        else:
            print("[INFO] LLM caching disabled (Redis not available)")

    def _generate_cache_key(self, prompt: str) -> str:
        """
        Generate cache key from prompt.

        Uses SHA256 hash of prompt combined with model version to create
        a unique, deterministic key. The model version ensures cache
        invalidation when the model is updated.

        Args:
            prompt: Full prompt text

        Returns:
            Redis cache key (e.g., "llm_response:qwen2.5-0.5b-q4:abc123...")
        """
        # Combine prompt with model version for cache key
        content = f"{self.model_version}:{prompt}"

        # Generate SHA256 hash
        prompt_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

        # Return full key with prefix
        return f"{self.key_prefix}{self.model_version}:{prompt_hash}"

    def get_cached_response(self, prompt: str) -> Optional[Dict]:
        """
        Retrieve cached response for a prompt.

        Args:
            prompt: Full prompt text (same as used for generation)

        Returns:
            Dictionary containing cached response if found:
            {
                "response": "Generated text...",
                "tokens_generated": 150,
                "timestamp": 1234567890,
                "cached": True,
                "cache_age_seconds": 3600
            }

            Returns None if not cached or cache disabled.
        """
        if not self.enabled or not self.redis_client:
            return None

        try:
            # Generate cache key
            cache_key = self._generate_cache_key(prompt)

            # Try to get from cache
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                # Parse cached JSON
                data = json.loads(cached_data)

                # Add cache metadata
                cache_age = time.time() - data.get('timestamp', time.time())
                data['cached'] = True
                data['cache_age_seconds'] = cache_age

                # Increment hit counter
                self._increment_stat('hits')

                return data
            else:
                # Cache miss
                self._increment_stat('misses')
                return None

        except (redis.RedisError, json.JSONDecodeError) as e:
            print(f"[WARN] Cache retrieval error: {e}")
            return None

    def cache_response(
        self,
        prompt: str,
        response: str,
        tokens_generated: int,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Store response in cache.

        Args:
            prompt: Full prompt text
            response: Generated response text
            tokens_generated: Number of tokens in response
            metadata: Optional additional metadata to store

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            # Generate cache key
            cache_key = self._generate_cache_key(prompt)

            # Prepare cache entry
            cache_entry = {
                "response": response,
                "tokens_generated": tokens_generated,
                "timestamp": time.time(),
                "model_version": self.model_version
            }

            # Add optional metadata
            if metadata:
                cache_entry['metadata'] = metadata

            # Store in Redis with TTL
            self.redis_client.setex(
                cache_key,
                self.ttl_seconds,
                json.dumps(cache_entry)
            )

            # Increment cache counter
            self._increment_stat('cached_responses')

            return True

        except redis.RedisError as e:
            print(f"[WARN] Cache storage error: {e}")
            return False

    def _increment_stat(self, stat_name: str):
        """Increment a cache statistic counter."""
        if not self.enabled or not self.redis_client:
            return

        try:
            stat_key = f"{self.key_prefix}stats:{stat_name}"
            self.redis_client.incr(stat_key)
        except redis.RedisError:
            pass  # Silently fail for stats (non-critical)

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary containing:
            {
                "hits": 150,
                "misses": 350,
                "total_queries": 500,
                "hit_rate": 0.30,
                "cached_responses": 200,
                "enabled": True
            }
        """
        if not self.enabled or not self.redis_client:
            return {
                "enabled": False,
                "hits": 0,
                "misses": 0,
                "total_queries": 0,
                "hit_rate": 0.0,
                "cached_responses": 0
            }

        try:
            # Get stat counters
            hits = int(self.redis_client.get(f"{self.key_prefix}stats:hits") or 0)
            misses = int(self.redis_client.get(f"{self.key_prefix}stats:misses") or 0)
            cached = int(self.redis_client.get(f"{self.key_prefix}stats:cached_responses") or 0)

            total_queries = hits + misses
            hit_rate = hits / total_queries if total_queries > 0 else 0.0

            return {
                "enabled": True,
                "hits": hits,
                "misses": misses,
                "total_queries": total_queries,
                "hit_rate": hit_rate,
                "cached_responses": cached
            }

        except redis.RedisError as e:
            print(f"[WARN] Error fetching cache stats: {e}")
            return {
                "enabled": False,
                "error": str(e)
            }

    def clear_cache(self) -> int:
        """
        Clear all cached responses.

        Returns:
            Number of cache entries cleared
        """
        if not self.enabled or not self.redis_client:
            return 0

        try:
            # Find all cache keys with our prefix
            pattern = f"{self.key_prefix}{self.model_version}:*"
            keys = self.redis_client.keys(pattern)

            if keys:
                # Delete all keys
                deleted = self.redis_client.delete(*keys)
                print(f"[OK] Cleared {deleted} cache entries")
                return deleted
            else:
                print("[INFO] No cache entries to clear")
                return 0

        except redis.RedisError as e:
            print(f"[ERROR] Failed to clear cache: {e}")
            return 0

    def get_cache_size(self) -> int:
        """
        Get number of cached responses.

        Returns:
            Number of cache entries for current model version
        """
        if not self.enabled or not self.redis_client:
            return 0

        try:
            pattern = f"{self.key_prefix}{self.model_version}:*"
            keys = self.redis_client.keys(pattern)
            return len(keys)
        except redis.RedisError:
            return 0

    def get_cache_memory_usage(self) -> Dict:
        """
        Get cache memory usage information.

        Returns:
            Dictionary with memory statistics
        """
        if not self.enabled or not self.redis_client:
            return {"enabled": False}

        try:
            info = self.redis_client.info('memory')
            return {
                "enabled": True,
                "used_memory_human": info.get('used_memory_human', 'N/A'),
                "used_memory_rss_human": info.get('used_memory_rss_human', 'N/A'),
                "maxmemory_human": info.get('maxmemory_human', 'N/A')
            }
        except redis.RedisError as e:
            return {"enabled": False, "error": str(e)}


# Example usage and testing
if __name__ == "__main__":
    print("=== LLM Response Cache Test ===\n")

    # Initialize cache
    cache = LLMResponseCache()

    if not cache.enabled:
        print("[ERROR] Cache not available. Ensure Redis is running:")
        print("  Windows: redis-server.exe")
        print("  Linux/Mac: redis-server")
        sys.exit(1)

    # Clear cache for clean test
    cache.clear_cache()

    # Test prompt
    prompt = "You are a helpful assistant. User: What is Python? Assistant:"

    # Test 1: Cache miss (first query)
    print("--- Test 1: Cache Miss ---")
    start = time.time()
    result = cache.get_cached_response(prompt)
    elapsed_ms = (time.time() - start) * 1000

    print(f"Result: {result}")
    print(f"Latency: {elapsed_ms:.2f}ms")
    assert result is None, "Should be cache miss"
    print("[OK] Cache miss as expected\n")

    # Test 2: Store response
    print("--- Test 2: Store Response ---")
    response = "Python is a high-level programming language."
    success = cache.cache_response(prompt, response, tokens_generated=12)
    print(f"Cached: {success}")
    assert success, "Should cache successfully"
    print("[OK] Response cached\n")

    # Test 3: Cache hit (retrieve cached)
    print("--- Test 3: Cache Hit ---")
    start = time.time()
    result = cache.get_cached_response(prompt)
    elapsed_ms = (time.time() - start) * 1000

    print(f"Result: {result is not None}")
    print(f"Response: {result['response'][:50]}...")
    print(f"Tokens: {result['tokens_generated']}")
    print(f"Latency: {elapsed_ms:.2f}ms")
    assert result is not None, "Should be cache hit"
    assert result['response'] == response, "Response should match"
    print(f"[OK] Cache hit (latency: {elapsed_ms:.0f}ms)\n")

    # Test 4: Cache stats
    print("--- Test 4: Cache Statistics ---")
    stats = cache.get_cache_stats()
    print(f"Hits: {stats['hits']}")
    print(f"Misses: {stats['misses']}")
    print(f"Hit rate: {stats['hit_rate']:.1%}")
    print(f"Cached responses: {stats['cached_responses']}")
    assert stats['hits'] == 1, "Should have 1 hit"
    assert stats['misses'] == 1, "Should have 1 miss"
    print("[OK] Stats tracking works\n")

    # Test 5: Cache size
    print("--- Test 5: Cache Size ---")
    size = cache.get_cache_size()
    print(f"Cache entries: {size}")
    assert size == 1, "Should have 1 entry"
    print("[OK] Cache size correct\n")

    # Test 6: Clear cache
    print("--- Test 6: Clear Cache ---")
    cleared = cache.clear_cache()
    print(f"Cleared entries: {cleared}")
    size_after = cache.get_cache_size()
    print(f"Cache entries after clear: {size_after}")
    assert size_after == 0, "Cache should be empty"
    print("[OK] Cache cleared\n")

    print("[OK] All tests passed")

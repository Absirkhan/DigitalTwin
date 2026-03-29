"""
LLM Generator - Response generation with streaming and caching

This module provides LLM-based response generation using llama.cpp for efficient
CPU inference. It integrates with the LLM cache for fast repeat queries and
supports streaming output for improved perceived latency.

Key Features:
- Qwen2.5-0.5B model with Q4_K_M quantization (~400MB)
- Streaming token generation (yields tokens as they generate)
- Redis-based response caching (<50ms for cache hits)
- Configurable temperature, top-p, top-k sampling
- Stop sequences to prevent rambling
- Latency tracking and performance metrics

Expected Performance (CPU, 4 threads):
- Cold start (first load): ~10-15s
- 200 token generation: ~3-4s (uncached)
- Cache hit: <50ms (60-80x faster)
- Time to first token (streaming): ~500-800ms

Usage:
    generator = LLMGenerator()

    # Non-streaming generation
    result = generator.generate_response(prompt, max_tokens=200)
    print(result['response'])  # Full response
    print(result['latency_ms'])  # 3000-4000ms or <50ms if cached

    # Streaming generation
    for chunk in generator.generate_response_stream(prompt, max_tokens=200):
        if chunk['type'] == 'token':
            print(chunk['content'], end='', flush=True)
        elif chunk['type'] == 'done':
            print(f"\\nGenerated {chunk['tokens_generated']} tokens")
"""

import time
from typing import Dict, Optional, Generator
from pathlib import Path
import sys

# Add parent directory to path for config import
sys.path.append(str(Path(__file__).parent.parent))

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    print("Warning: llama-cpp-python not installed.")
    print("Install with: pip install llama-cpp-python")

from rag.llm_cache import LLMResponseCache
from config import RAGConfig


class LLMGenerator:
    """
    LLM-based response generator with caching and streaming.

    This class loads a GGUF model via llama.cpp and provides methods for
    generating responses. It integrates with LLMResponseCache for fast
    repeat queries and supports streaming for improved UX.

    Attributes:
        llm: Llama model instance (or None if not available)
        cache: LLMResponseCache instance
        config: RAGConfig instance
        model_loaded: Whether model is successfully loaded
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        cache_enabled: bool = True,
        verbose: bool = False
    ):
        """
        Initialize LLM generator.

        Args:
            model_path: Path to GGUF model file (uses config default if None)
            cache_enabled: Enable response caching
            verbose: Enable verbose logging
        """
        self.config = RAGConfig
        self.model_path = model_path or self.config.MODEL_PATH
        self.verbose = verbose
        self.model_loaded = False
        self.llm = None

        # Initialize cache
        self.cache = LLMResponseCache(
            redis_url=self.config.CACHE_REDIS_URL,
            key_prefix=self.config.CACHE_KEY_PREFIX,
            ttl_seconds=self.config.CACHE_TTL_SECONDS,
            enabled=cache_enabled,
            model_version="qwen2.5-0.5b-q4"
        )

        # Load model
        if LLAMA_CPP_AVAILABLE:
            self._load_model()
        else:
            print("[ERROR] llama-cpp-python not available. Cannot load model.")

    def _load_model(self):
        """
        Load GGUF model with llama.cpp.

        This method loads the model into memory and configures inference
        parameters. First load takes 10-15s, but subsequent inferences
        are much faster (3-4s for 200 tokens).
        """
        if not Path(self.model_path).exists():
            print(f"[ERROR] Model file not found: {self.model_path}")
            print("Please download the model. See models/README.md for instructions.")
            return

        print(f"Loading model from: {self.model_path}")
        print("This may take 10-15 seconds on first load...")

        start_time = time.time()

        try:
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self.config.MODEL_CONTEXT_SIZE,
                n_threads=self.config.MODEL_CPU_THREADS,
                n_gpu_layers=self.config.MODEL_GPU_LAYERS,
                verbose=self.verbose
            )

            load_time = time.time() - start_time
            self.model_loaded = True
            print(f"[OK] Model loaded in {load_time:.1f}s")

        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")
            self.model_loaded = False

    def generate_response(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        use_cache: bool = True
    ) -> Dict:
        """
        Generate response for a prompt (non-streaming).

        This method first checks the cache for a matching response. If found,
        it returns instantly (<50ms). Otherwise, it generates a new response
        using the LLM (3-4s) and caches it for future queries.

        Args:
            prompt: Full prompt text (including RAG context)
            max_tokens: Maximum tokens to generate (default from config)
            temperature: Sampling temperature (default from config)
            top_p: Nucleus sampling parameter (default from config)
            top_k: Top-k sampling parameter (default from config)
            use_cache: Whether to use cache (default True)

        Returns:
            Dictionary containing:
            {
                "response": "Generated text...",
                "tokens_generated": 150,
                "latency_ms": 3240.5,
                "cached": False,
                "cache_age_seconds": 0,  # Only if cached=True
                "time_to_first_token_ms": 520.3  # Only if not cached
            }
        """
        if not self.model_loaded or not self.llm:
            return {
                "error": "Model not loaded",
                "response": "",
                "tokens_generated": 0,
                "latency_ms": 0,
                "cached": False
            }

        # Try cache first
        if use_cache:
            start_cache = time.time()
            cached_result = self.cache.get_cached_response(prompt)
            cache_latency = (time.time() - start_cache) * 1000

            if cached_result:
                if self.verbose:
                    print(f"[CACHE HIT] Returned in {cache_latency:.1f}ms")
                return {
                    "response": cached_result['response'],
                    "tokens_generated": cached_result['tokens_generated'],
                    "latency_ms": cache_latency,
                    "cached": True,
                    "cache_age_seconds": cached_result.get('cache_age_seconds', 0)
                }

        # Cache miss - generate new response
        if self.verbose:
            print("[CACHE MISS] Generating new response...")

        # Use config defaults if not specified
        max_tokens = max_tokens or self.config.MODEL_MAX_OUTPUT_TOKENS
        temperature = temperature if temperature is not None else self.config.MODEL_TEMPERATURE
        top_p = top_p if top_p is not None else self.config.MODEL_TOP_P
        top_k = top_k if top_k is not None else self.config.MODEL_TOP_K

        # Generate response
        start_time = time.time()
        time_to_first_token = None

        try:
            output = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=self.config.MODEL_STOP_SEQUENCES,
                repeat_penalty=self.config.MODEL_REPEAT_PENALTY,
                echo=False
            )

            # Extract response
            response_text = output['choices'][0]['text'].strip()
            tokens_generated = output['usage']['completion_tokens']

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Cache the response
            if use_cache:
                self.cache.cache_response(
                    prompt=prompt,
                    response=response_text,
                    tokens_generated=tokens_generated,
                    metadata={"latency_ms": latency_ms}
                )

            return {
                "response": response_text,
                "tokens_generated": tokens_generated,
                "latency_ms": latency_ms,
                "cached": False
            }

        except Exception as e:
            print(f"[ERROR] Generation failed: {e}")
            return {
                "error": str(e),
                "response": "",
                "tokens_generated": 0,
                "latency_ms": (time.time() - start_time) * 1000,
                "cached": False
            }

    def generate_response_stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        use_cache: bool = True
    ) -> Generator[Dict, None, None]:
        """
        Generate response with streaming (yields tokens as they generate).

        This method provides improved perceived latency by yielding tokens
        as they're generated, rather than waiting for the full response.
        Users see the first token in ~500-800ms instead of waiting 3-4s.

        Note: Cache hits return the full response immediately (non-streaming).

        Args:
            prompt: Full prompt text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            use_cache: Whether to check cache first

        Yields:
            Dictionaries with different types:

            {"type": "token", "content": "Hello"}
            {"type": "token", "content": " world"}
            {"type": "done", "tokens_generated": 150, "latency_ms": 3240.5}
            {"type": "error", "error": "..."}
        """
        if not self.model_loaded or not self.llm:
            yield {
                "type": "error",
                "error": "Model not loaded"
            }
            return

        # Try cache first
        if use_cache:
            cached_result = self.cache.get_cached_response(prompt)
            if cached_result:
                # Cache hit - return full response immediately
                yield {
                    "type": "token",
                    "content": cached_result['response']
                }
                yield {
                    "type": "done",
                    "tokens_generated": cached_result['tokens_generated'],
                    "latency_ms": cached_result.get('cache_age_seconds', 0) * 1000,
                    "cached": True
                }
                return

        # Cache miss - stream generation
        max_tokens = max_tokens or self.config.MODEL_MAX_OUTPUT_TOKENS
        temperature = temperature if temperature is not None else self.config.MODEL_TEMPERATURE
        top_p = top_p if top_p is not None else self.config.MODEL_TOP_P
        top_k = top_k if top_k is not None else self.config.MODEL_TOP_K

        start_time = time.time()
        full_response = ""
        tokens_generated = 0

        try:
            # Create streaming completion
            stream = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=self.config.MODEL_STOP_SEQUENCES,
                repeat_penalty=self.config.MODEL_REPEAT_PENALTY,
                stream=True,
                echo=False
            )

            # Yield tokens as they arrive
            for output in stream:
                if 'choices' in output and len(output['choices']) > 0:
                    choice = output['choices'][0]
                    if 'text' in choice:
                        token = choice['text']
                        full_response += token
                        tokens_generated += 1

                        yield {
                            "type": "token",
                            "content": token
                        }

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Cache the full response
            if use_cache and full_response:
                self.cache.cache_response(
                    prompt=prompt,
                    response=full_response.strip(),
                    tokens_generated=tokens_generated,
                    metadata={"latency_ms": latency_ms}
                )

            # Yield completion
            yield {
                "type": "done",
                "tokens_generated": tokens_generated,
                "latency_ms": latency_ms,
                "cached": False
            }

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e)
            }

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache hit rate, total queries, etc.
        """
        return self.cache.get_cache_stats()

    def clear_cache(self) -> int:
        """
        Clear all cached responses.

        Returns:
            Number of cache entries cleared
        """
        return self.cache.clear_cache()


# Example usage and testing
if __name__ == "__main__":
    print("=== LLM Generator Test ===\n")

    # Check if llama-cpp is available
    if not LLAMA_CPP_AVAILABLE:
        print("[ERROR] llama-cpp-python not installed")
        print("Install with: pip install llama-cpp-python")
        sys.exit(1)

    # Initialize generator
    print("Initializing LLM generator...")
    generator = LLMGenerator(verbose=True)

    if not generator.model_loaded:
        print("\n[ERROR] Model failed to load")
        print("Please ensure:")
        print("1. Model file exists at:", generator.model_path)
        print("2. See models/README.md for download instructions")
        sys.exit(1)

    # Clear cache for clean test
    generator.clear_cache()

    # Test prompt
    prompt = """You are a helpful AI assistant. Provide clear, accurate, and helpful responses.

User: What is Python?
Assistant:"""

    # Test 1: Non-streaming generation (cache miss)
    print("\n--- Test 1: Non-Streaming Generation (Cache Miss) ---")
    result = generator.generate_response(prompt, max_tokens=100)

    print(f"Response: {result['response'][:100]}...")
    print(f"Tokens: {result['tokens_generated']}")
    print(f"Latency: {result['latency_ms']:.0f}ms")
    print(f"Cached: {result['cached']}")

    # Test 2: Non-streaming generation (cache hit)
    print("\n--- Test 2: Non-Streaming Generation (Cache Hit) ---")
    result2 = generator.generate_response(prompt, max_tokens=100)

    print(f"Response: {result2['response'][:100]}...")
    print(f"Latency: {result2['latency_ms']:.0f}ms")
    print(f"Cached: {result2['cached']}")
    if result2['latency_ms'] > 0:
        print(f"Speedup: {result['latency_ms'] / result2['latency_ms']:.0f}x faster")
    else:
        print(f"Speedup: Instant (cache latency too fast to measure)")

    # Test 3: Streaming generation
    print("\n--- Test 3: Streaming Generation ---")
    prompt2 = """You are a helpful AI assistant.

User: Count from 1 to 5.
Assistant:"""

    print("Streaming response: ", end='', flush=True)
    for chunk in generator.generate_response_stream(prompt2, max_tokens=50):
        if chunk['type'] == 'token':
            print(chunk['content'], end='', flush=True)
        elif chunk['type'] == 'done':
            print(f"\n\nTokens: {chunk['tokens_generated']}")
            print(f"Latency: {chunk['latency_ms']:.0f}ms")

    # Test 4: Cache statistics
    print("\n--- Test 4: Cache Statistics ---")
    stats = generator.get_cache_stats()
    print(f"Hits: {stats['hits']}")
    print(f"Misses: {stats['misses']}")
    print(f"Hit rate: {stats['hit_rate']:.1%}")
    print(f"Total queries: {stats['total_queries']}")

    print("\n[OK] All tests complete")

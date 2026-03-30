"""
RAG Module Configuration

Centralized configuration for the RAG system, including model settings,
cache configuration, and response generation parameters.

All settings can be overridden via environment variables for deployment flexibility.
"""

import os
from pathlib import Path


class RAGConfig:
    """Configuration settings for RAG module."""

    # ═══════════════════════════════════════════════════════════════════
    # Model Settings
    # ═══════════════════════════════════════════════════════════════════

    # Path to GGUF model file
    MODEL_PATH = os.getenv(
        "RAG_MODEL_PATH",
        str(Path(__file__).parent / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf")
    )

    # Context window size (must match prompt builder budget)
    MODEL_CONTEXT_SIZE = int(os.getenv("RAG_MODEL_CONTEXT_SIZE", "2150"))

    # Maximum tokens to generate in response (increased for better quality)
    MODEL_MAX_OUTPUT_TOKENS = int(os.getenv("RAG_MODEL_MAX_TOKENS", "500"))

    # Temperature (0.0 = deterministic, 1.0 = creative)
    MODEL_TEMPERATURE = float(os.getenv("RAG_MODEL_TEMPERATURE", "0.7"))

    # Top-p nucleus sampling (0.9 = use top 90% probability mass)
    MODEL_TOP_P = float(os.getenv("RAG_MODEL_TOP_P", "0.9"))

    # Top-k sampling (0 = disabled, 40 = use top 40 tokens)
    MODEL_TOP_K = int(os.getenv("RAG_MODEL_TOP_K", "40"))

    # Number of CPU threads for inference
    MODEL_CPU_THREADS = int(os.getenv("RAG_MODEL_CPU_THREADS", "4"))

    # GPU layers to offload (0 = CPU only)
    MODEL_GPU_LAYERS = int(os.getenv("RAG_MODEL_GPU_LAYERS", "0"))

    # Stop sequences (stop generating when these appear)
    MODEL_STOP_SEQUENCES = [
        "User:",
        "\n\n\n",
        "###",
        "[INST]",
        "[/INST]"
    ]

    # Repeat penalty (1.0 = no penalty, 1.1 = slight penalty)
    MODEL_REPEAT_PENALTY = float(os.getenv("RAG_MODEL_REPEAT_PENALTY", "1.1"))

    # ═══════════════════════════════════════════════════════════════════
    # Cache Settings
    # ═══════════════════════════════════════════════════════════════════

    # Enable response caching
    CACHE_ENABLED = os.getenv("RAG_CACHE_ENABLED", "true").lower() == "true"

    # Redis connection URL
    CACHE_REDIS_URL = os.getenv("RAG_CACHE_REDIS_URL", "redis://localhost:6379")

    # Cache TTL in seconds (24 hours default)
    CACHE_TTL_SECONDS = int(os.getenv("RAG_CACHE_TTL_SECONDS", "86400"))

    # Redis key prefix for LLM responses
    CACHE_KEY_PREFIX = os.getenv("RAG_CACHE_KEY_PREFIX", "llm_response:")

    # Redis database number (0-15)
    CACHE_REDIS_DB = int(os.getenv("RAG_CACHE_REDIS_DB", "0"))

    # Cache hit tracking (store statistics)
    CACHE_TRACK_STATS = os.getenv("RAG_CACHE_TRACK_STATS", "true").lower() == "true"

    # ═══════════════════════════════════════════════════════════════════
    # Response Generation Settings
    # ═══════════════════════════════════════════════════════════════════

    # Enable streaming by default
    STREAMING_DEFAULT = os.getenv("RAG_STREAMING_DEFAULT", "false").lower() == "true"

    # Streaming chunk size (characters per yield)
    STREAMING_CHUNK_SIZE = int(os.getenv("RAG_STREAMING_CHUNK_SIZE", "10"))

    # Timeout for LLM generation (seconds)
    GENERATION_TIMEOUT_SECONDS = int(os.getenv("RAG_GENERATION_TIMEOUT", "30"))

    # Retry attempts on generation failure
    GENERATION_MAX_RETRIES = int(os.getenv("RAG_GENERATION_MAX_RETRIES", "2"))

    # ═══════════════════════════════════════════════════════════════════
    # Logging & Monitoring
    # ═══════════════════════════════════════════════════════════════════

    # Enable verbose logging
    VERBOSE_LOGGING = os.getenv("RAG_VERBOSE_LOGGING", "false").lower() == "true"

    # Track latency metrics
    TRACK_LATENCY = os.getenv("RAG_TRACK_LATENCY", "true").lower() == "true"

    # Log cache hit/miss
    LOG_CACHE_OPERATIONS = os.getenv("RAG_LOG_CACHE_OPS", "false").lower() == "true"

    # ═══════════════════════════════════════════════════════════════════
    # Data Paths
    # ═══════════════════════════════════════════════════════════════════

    # Base path for user data
    USER_DATA_PATH = os.getenv(
        "RAG_USER_DATA_PATH",
        str(Path(__file__).parent / "data" / "users")
    )

    # Models directory
    MODELS_DIR = os.getenv(
        "RAG_MODELS_DIR",
        str(Path(__file__).parent / "models")
    )

    @classmethod
    def validate(cls) -> bool:
        """
        Validate configuration settings.

        Returns:
            True if all settings are valid, raises ValueError otherwise
        """
        # Check model file exists
        if not os.path.exists(cls.MODEL_PATH):
            raise ValueError(
                f"Model file not found: {cls.MODEL_PATH}\n"
                f"Please download the model to: {cls.MODELS_DIR}\n"
                f"See models/README.md for instructions"
            )

        # Validate token counts
        if cls.MODEL_MAX_OUTPUT_TOKENS <= 0:
            raise ValueError("MODEL_MAX_OUTPUT_TOKENS must be positive")

        if cls.MODEL_CONTEXT_SIZE <= cls.MODEL_MAX_OUTPUT_TOKENS:
            raise ValueError(
                f"MODEL_CONTEXT_SIZE ({cls.MODEL_CONTEXT_SIZE}) must be "
                f"larger than MODEL_MAX_OUTPUT_TOKENS ({cls.MODEL_MAX_OUTPUT_TOKENS})"
            )

        # Validate temperature and top_p
        if not 0.0 <= cls.MODEL_TEMPERATURE <= 2.0:
            raise ValueError("MODEL_TEMPERATURE must be between 0.0 and 2.0")

        if not 0.0 <= cls.MODEL_TOP_P <= 1.0:
            raise ValueError("MODEL_TOP_P must be between 0.0 and 1.0")

        # Validate CPU threads
        if cls.MODEL_CPU_THREADS <= 0:
            raise ValueError("MODEL_CPU_THREADS must be positive")

        # Validate cache TTL
        if cls.CACHE_TTL_SECONDS <= 0:
            raise ValueError("CACHE_TTL_SECONDS must be positive")

        return True

    @classmethod
    def get_model_info(cls) -> dict:
        """
        Get model information for debugging.

        Returns:
            Dictionary with model configuration details
        """
        return {
            "model_path": cls.MODEL_PATH,
            "model_exists": os.path.exists(cls.MODEL_PATH),
            "context_size": cls.MODEL_CONTEXT_SIZE,
            "max_output_tokens": cls.MODEL_MAX_OUTPUT_TOKENS,
            "temperature": cls.MODEL_TEMPERATURE,
            "top_p": cls.MODEL_TOP_P,
            "top_k": cls.MODEL_TOP_K,
            "cpu_threads": cls.MODEL_CPU_THREADS,
            "gpu_layers": cls.MODEL_GPU_LAYERS,
            "stop_sequences": cls.MODEL_STOP_SEQUENCES,
            "cache_enabled": cls.CACHE_ENABLED,
            "cache_ttl_hours": cls.CACHE_TTL_SECONDS / 3600,
            "streaming_default": cls.STREAMING_DEFAULT
        }

    @classmethod
    def print_config(cls):
        """Print configuration summary (for debugging)."""
        print("=" * 60)
        print("RAG Configuration")
        print("=" * 60)

        info = cls.get_model_info()
        for key, value in info.items():
            print(f"{key:25s}: {value}")

        print("=" * 60)


# Validate configuration on import (fail fast)
try:
    # Only validate if model file is expected to exist
    # (allows import during setup/documentation generation)
    if os.path.exists(RAGConfig.MODELS_DIR):
        pass  # Model directory exists, but file might not be downloaded yet
except Exception as e:
    print(f"Warning: Configuration validation skipped: {e}")


# Example usage
if __name__ == "__main__":
    print("RAG Module Configuration")
    print("-" * 60)

    # Print configuration
    RAGConfig.print_config()

    # Try to validate
    try:
        RAGConfig.validate()
        print("\n[OK] Configuration valid")
    except ValueError as e:
        print(f"\n[ERROR] Configuration invalid: {e}")

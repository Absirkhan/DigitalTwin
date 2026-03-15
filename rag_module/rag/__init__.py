"""
RAG Module - Ultra-Low-Latency Retrieval System

This module provides a standalone RAG (Retrieval Augmented Generation) pipeline
optimized for real-time voice assistant applications.

Key Features:
- Sub-millisecond retrieval using FAISS vector search
- User-specific conversation memory with complete data isolation
- Automatic user profile building from conversation patterns
- Token budget enforcement for LLM context management
- CPU-only operation with no external API dependencies

Architecture:
- FAISS IndexFlatL2 for exact nearest neighbor search (~0.3ms latency)
- sentence-transformers all-MiniLM-L6-v2 for embeddings (384-dim)
- Manual persistence (FAISS index + JSON metadata)
- Session memory + long-term vector storage

Designed for integration into voice assistant pipelines where latency matters.
"""

__version__ = "1.0.0"
__author__ = "DigitalTwin RAG Team"

from rag.embedder import EmbeddingEngine
from rag.faiss_store import FAISSStore
from rag.retriever import ContextRetriever
from rag.profile_manager import UserProfileManager
from rag.memory_manager import SessionMemory
from rag.prompt_builder import PromptBuilder
from rag.pipeline import RAGPipeline

__all__ = [
    "EmbeddingEngine",
    "FAISSStore",
    "ContextRetriever",
    "UserProfileManager",
    "SessionMemory",
    "PromptBuilder",
    "RAGPipeline",
]

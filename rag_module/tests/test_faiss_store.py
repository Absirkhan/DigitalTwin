"""
FAISS Store Tests

Tests for FAISSStore module covering:
- Exchange storage and retrieval
- Index persistence (save/load)
- User data isolation
- Search accuracy
- Metadata consistency
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import numpy as np
import pytest
from rag.faiss_store import FAISSStore
from rag.embedder import EmbeddingEngine


class TestFAISSStore:
    """Test suite for FAISS vector store."""

    @pytest.fixture
    def embedder(self):
        """Create embedding engine for tests."""
        return EmbeddingEngine()

    @pytest.fixture
    def test_user_id(self):
        """Test user ID."""
        return "test_user_faiss"

    @pytest.fixture
    def store(self, test_user_id):
        """Create fresh FAISS store for each test."""
        base_path = Path(__file__).parent.parent / "data" / "users"
        store = FAISSStore(test_user_id, base_path=str(base_path))

        # Clean up any existing data
        store.delete_user_data()

        yield store

        # Cleanup after test
        store.delete_user_data()

    def test_add_single_exchange(self, store, embedder):
        """Test adding a single exchange and verifying it's stored."""
        user_text = "What is FAISS?"
        assistant_text = "FAISS is a library for similarity search."
        exchange_text = f"User: {user_text}\nAssistant: {assistant_text}"

        # Generate embedding
        embedding = embedder.embed(exchange_text).reshape(1, -1)

        # Add exchange
        store.add_exchange("exch_1", user_text, assistant_text, embedding)

        # Verify it was added
        assert store.get_total_exchanges() == 1

        # Verify we can retrieve it
        results = store.search(embedding, top_k=1)
        assert len(results) == 1
        assert results[0]['user_text'] == user_text
        assert results[0]['assistant_text'] == assistant_text

    def test_index_persistence(self, test_user_id, embedder):
        """Test that index persists to disk and reloads correctly."""
        base_path = Path(__file__).parent.parent / "data" / "users"

        # Create store and add data
        store1 = FAISSStore(test_user_id, base_path=str(base_path))
        store1.delete_user_data()  # Start clean

        user_text = "How do I use FAISS?"
        assistant_text = "Install with: pip install faiss-cpu"
        exchange_text = f"User: {user_text}\nAssistant: {assistant_text}"
        embedding = embedder.embed(exchange_text).reshape(1, -1)

        store1.add_exchange("exch_1", user_text, assistant_text, embedding)
        assert store1.get_total_exchanges() == 1

        # Create new store instance (should load from disk)
        store2 = FAISSStore(test_user_id, base_path=str(base_path))
        assert store2.get_total_exchanges() == 1

        # Verify data is same
        results = store2.search(embedding, top_k=1)
        assert len(results) == 1
        assert results[0]['user_text'] == user_text

        # Cleanup
        store2.delete_user_data()

    def test_search_returns_correct_number(self, store, embedder):
        """Test that search returns requested number of results."""
        # Add 5 exchanges
        for i in range(5):
            text = f"Exchange {i}"
            emb = embedder.embed(text).reshape(1, -1)
            store.add_exchange(f"exch_{i}", text, f"Response {i}", emb)

        assert store.get_total_exchanges() == 5

        # Search for top 3
        query_emb = embedder.embed("Exchange").reshape(1, -1)
        results = store.search(query_emb, top_k=3)

        assert len(results) == 3

        # Search for top 10 (but only 5 exist)
        results = store.search(query_emb, top_k=10)
        assert len(results) == 5

    def test_user_isolation(self, embedder):
        """Test that two users have completely isolated indexes."""
        base_path = Path(__file__).parent.parent / "data" / "users"

        # Create stores for two users
        store1 = FAISSStore("user_1", base_path=str(base_path))
        store2 = FAISSStore("user_2", base_path=str(base_path))

        # Clean up
        store1.delete_user_data()
        store2.delete_user_data()

        # Add data to user 1
        emb1 = embedder.embed("User 1 data").reshape(1, -1)
        store1.add_exchange("exch_1", "User 1 message", "Response 1", emb1)

        # Add data to user 2
        emb2 = embedder.embed("User 2 data").reshape(1, -1)
        store2.add_exchange("exch_1", "User 2 message", "Response 2", emb2)

        # Verify isolation
        assert store1.get_total_exchanges() == 1
        assert store2.get_total_exchanges() == 1

        # Search in store1 should only find user1 data
        results1 = store1.search(emb1, top_k=10)
        assert len(results1) == 1
        assert results1[0]['user_text'] == "User 1 message"

        # Search in store2 should only find user2 data
        results2 = store2.search(emb2, top_k=10)
        assert len(results2) == 1
        assert results2[0]['user_text'] == "User 2 message"

        # Cleanup
        store1.delete_user_data()
        store2.delete_user_data()

    def test_delete_clears_data(self, store, embedder):
        """Test that delete removes both index and metadata."""
        # Add some data
        emb = embedder.embed("Test data").reshape(1, -1)
        store.add_exchange("exch_1", "Test", "Response", emb)
        assert store.get_total_exchanges() == 1

        # Delete
        store.delete_user_data()

        # Verify empty
        assert store.get_total_exchanges() == 0

        # Verify files are gone
        assert not store.index_path.exists()
        assert not store.metadata_path.exists()

    def test_similarity_scores(self, store, embedder):
        """Test that similarity scores are computed correctly."""
        # Add exchanges
        exchanges = [
            ("What is machine learning?", "ML is a subset of AI."),
            ("How does neural network work?", "Neural networks use layers."),
            ("What's the weather today?", "I don't have weather data.")
        ]

        for i, (user_msg, asst_msg) in enumerate(exchanges):
            text = f"User: {user_msg}\nAssistant: {asst_msg}"
            emb = embedder.embed(text).reshape(1, -1)
            store.add_exchange(f"exch_{i}", user_msg, asst_msg, emb)

        # Query similar to first exchange
        query = "Tell me about machine learning"
        query_emb = embedder.embed(query).reshape(1, -1)

        results = store.search(query_emb, top_k=3)

        # First result should be most similar (highest score)
        assert len(results) == 3
        assert results[0]['similarity_score'] >= results[1]['similarity_score']
        assert results[1]['similarity_score'] >= results[2]['similarity_score']

        # First result should be the ML question
        assert "machine learning" in results[0]['user_text'].lower()

    def test_empty_store_search(self, store, embedder):
        """Test searching an empty store returns empty list."""
        query_emb = embedder.embed("test query").reshape(1, -1)
        results = store.search(query_emb, top_k=5)

        assert results == []


def test_runner():
    """Run all tests manually without pytest."""
    print("=== Running FAISS Store Tests ===\n")

    embedder = EmbeddingEngine()
    test_user_id = "test_user_manual"
    base_path = Path(__file__).parent.parent / "data" / "users"

    # Test 1: Add and retrieve
    print("Test 1: Add and retrieve single exchange...")
    store = FAISSStore(test_user_id, base_path=str(base_path))
    store.delete_user_data()

    emb = embedder.embed("Test message").reshape(1, -1)
    store.add_exchange("exch_1", "Test", "Response", emb)
    assert store.get_total_exchanges() == 1
    print("  ✓ PASSED\n")

    # Test 2: Persistence
    print("Test 2: Index persistence...")
    store2 = FAISSStore(test_user_id, base_path=str(base_path))
    assert store2.get_total_exchanges() == 1
    print("  ✓ PASSED\n")

    # Test 3: Search
    print("Test 3: Search returns correct results...")
    results = store2.search(emb, top_k=1)
    assert len(results) == 1
    assert results[0]['user_text'] == "Test"
    print("  ✓ PASSED\n")

    # Cleanup
    store2.delete_user_data()

    print("✓ All FAISS Store tests passed!\n")


if __name__ == "__main__":
    # Run manual test if pytest not available
    try:
        import pytest
        pytest.main([__file__, "-v"])
    except ImportError:
        print("pytest not found, running manual tests...\n")
        test_runner()

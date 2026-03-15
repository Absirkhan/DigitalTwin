"""
Retriever Tests

Tests for ContextRetriever covering:
- Ranked retrieval results
- Threshold filtering
- Context formatting
- Latency measurement
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from rag.embedder import EmbeddingEngine
from rag.faiss_store import FAISSStore
from rag.retriever import ContextRetriever


def test_retrieve_returns_ranked_results():
    """Test that retrieve returns results ranked by similarity."""
    print("Test: Retrieve returns ranked results...")

    embedder = EmbeddingEngine()
    user_id = "test_user_retriever"

    # Setup store - use absolute path
    base_path = Path(__file__).parent.parent / "data" / "users"

    # Initialize retriever with the same base_path
    # NOTE: We need to manually inject the store to avoid path mismatch
    store = FAISSStore(user_id, base_path=str(base_path))
    store.delete_user_data()

    # Create retriever AFTER store is ready
    retriever = ContextRetriever(embedder)

    # Add test data directly to store
    # This data will be persisted and loaded by the retriever
    exchanges = [
        ("I have a bug in my code", "Let me help debug."),
        ("What is FAISS?", "FAISS is a similarity search library."),
        ("How do I fix errors?", "Check the error message.")
    ]

    for i, (user_msg, asst_msg) in enumerate(exchanges):
        text = f"User: {user_msg}\nAssistant: {asst_msg}"
        emb = embedder.embed(text).reshape(1, -1)
        store.add_exchange(f"exch_{i}", user_msg, asst_msg, emb)

    # Verify data was added
    assert store.get_total_exchanges() == 3, f"Expected 3 exchanges, got {store.get_total_exchanges()}"

    # Manually inject the store into the retriever to ensure they use the same instance
    retriever.stores[user_id] = store

    # Retrieve using retriever
    results = retriever.retrieve(user_id, "error in my code", top_k=3)

    # Debug output
    print(f"  Retrieved {len(results)} results (expected 3)")

    # Verify ranked
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    assert results[0]['rank'] == 1
    assert results[1]['rank'] == 2
    assert results[2]['rank'] == 3

    # Verify similarity scores are descending
    assert results[0]['similarity_score'] >= results[1]['similarity_score']
    assert results[1]['similarity_score'] >= results[2]['similarity_score']

    # Cleanup
    store.delete_user_data()
    print("  [OK] PASSED\n")


def test_threshold_filtering():
    """Test that threshold filtering removes low similarity results."""
    print("Test: Threshold filtering...")

    embedder = EmbeddingEngine()
    user_id = "test_user_threshold"

    # Setup
    base_path = Path(__file__).parent.parent / "data" / "users"
    store = FAISSStore(user_id, base_path=str(base_path))
    store.delete_user_data()

    retriever = ContextRetriever(embedder)

    # Add diverse data
    exchanges = [
        ("What is machine learning?", "ML is a subset of AI."),
        ("Tell me about the weather", "I don't have weather data."),
        ("Explain neural networks", "Neural networks use layers.")
    ]

    for i, (user_msg, asst_msg) in enumerate(exchanges):
        text = f"User: {user_msg}\nAssistant: {asst_msg}"
        emb = embedder.embed(text).reshape(1, -1)
        store.add_exchange(f"exch_{i}", user_msg, asst_msg, emb)

    # Inject store into retriever
    retriever.stores[user_id] = store

    # Retrieve with high threshold
    results = retriever.retrieve_above_threshold(
        user_id, "machine learning algorithms", threshold=0.7, max_results=3
    )

    # Should only get highly relevant results
    assert len(results) <= 3
    if results:
        assert all(r['similarity_score'] >= 0.7 for r in results)

    # Cleanup
    store.delete_user_data()
    print("  [OK] PASSED\n")


def test_format_context():
    """Test that format_context returns clean string."""
    print("Test: Format context...")

    embedder = EmbeddingEngine()
    user_id = "test_user_format"

    # Setup
    base_path = Path(__file__).parent.parent / "data" / "users"
    store = FAISSStore(user_id, base_path=str(base_path))
    store.delete_user_data()

    retriever = ContextRetriever(embedder)

    # Add data
    emb = embedder.embed("Test").reshape(1, -1)
    store.add_exchange("exch_1", "Question", "Answer", emb)

    # Inject store into retriever
    retriever.stores[user_id] = store

    # Retrieve and format
    results = retriever.retrieve(user_id, "Question", top_k=1)
    formatted = retriever.format_context(results)

    # Verify format
    assert isinstance(formatted, str)
    assert len(formatted) > 0
    assert "[Past Exchange 1" in formatted
    assert "Question" in formatted
    assert "Answer" in formatted

    # Test empty results
    empty_formatted = retriever.format_context([])
    assert empty_formatted == ""

    # Cleanup
    store.delete_user_data()
    print("  [OK] PASSED\n")


def test_latency_measurement():
    """Test that retrieval latency is under 10ms."""
    print("Test: Latency measurement...")

    embedder = EmbeddingEngine()
    user_id = "test_user_latency"

    # Setup
    base_path = Path(__file__).parent.parent / "data" / "users"
    store = FAISSStore(user_id, base_path=str(base_path))
    store.delete_user_data()

    retriever = ContextRetriever(embedder)

    # Add test data
    for i in range(10):
        text = f"Exchange {i}"
        emb = embedder.embed(text).reshape(1, -1)
        store.add_exchange(f"exch_{i}", text, f"Response {i}", emb)

    # Inject store into retriever
    retriever.stores[user_id] = store

    # Measure latency
    data = retriever.measure_retrieval_latency(user_id, "Exchange 5")

    # Verify latency is reasonable (< 10ms is conservative, should be < 1ms)
    assert data['latency_ms'] < 10
    assert len(data['results']) > 0

    print(f"    Latency: {data['latency_ms']:.3f}ms")

    # Cleanup
    store.delete_user_data()
    print("  [OK] PASSED\n")


def run_all_tests():
    """Run all retriever tests."""
    print("=== Running Retriever Tests ===\n")

    test_retrieve_returns_ranked_results()
    test_threshold_filtering()
    test_format_context()
    test_latency_measurement()

    print("[OK] All Retriever tests passed!\n")


if __name__ == "__main__":
    run_all_tests()

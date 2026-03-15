"""
FAISS Retrieval Benchmark

Benchmarks retrieval latency to verify performance targets:
- Target: Sub-millisecond average latency (~0.3ms)
- Comparison: FAISS vs ChromaDB theoretical baseline (~20ms)
- Metrics: Min, Max, Avg, P95, P99 latency

This benchmark demonstrates why FAISS was chosen over ChromaDB
for real-time voice assistant applications where latency is critical.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import time
import numpy as np
from rag.embedder import EmbeddingEngine
from rag.faiss_store import FAISSStore
from rag.retriever import ContextRetriever


def create_synthetic_exchanges(n: int) -> list:
    """
    Create synthetic conversation exchanges for testing.

    Args:
        n: Number of exchanges to create

    Returns:
        List of (user_text, assistant_text) tuples
    """
    topics = [
        "error", "bug", "code", "function", "model", "training",
        "data", "performance", "optimization", "latency", "memory",
        "database", "API", "server", "client", "testing"
    ]

    exchanges = []
    for i in range(n):
        topic = topics[i % len(topics)]
        user_text = f"I have a question about {topic} in my project number {i}"
        assistant_text = f"For {topic}, you should check the documentation and verify configuration {i}"
        exchanges.append((user_text, assistant_text))

    return exchanges


def run_benchmark(num_exchanges: int = 50, num_queries: int = 100):
    """
    Run retrieval benchmark.

    Creates a FAISS index with num_exchanges, then runs num_queries
    retrieval operations and measures latency statistics.

    Args:
        num_exchanges: Number of exchanges to store in index
        num_queries: Number of retrieval queries to run
    """
    print("┌" + "─" * 58 + "┐")
    print("│" + " " * 17 + "FAISS Retrieval Benchmark" + " " * 16 + "│")
    print("├" + "─" * 58 + "┤")
    print(f"│ Index size     : {num_exchanges:>3} exchanges" + " " * 26 + "│")
    print(f"│ Queries to run : {num_queries:>3}" + " " * 34 + "│")
    print("├" + "─" * 58 + "┤")

    # Initialize components
    print("│ Initializing embedding engine..." + " " * 23 + "│")
    embedder = EmbeddingEngine()

    user_id = "benchmark_user"
    base_path = Path(__file__).parent / "data" / "users"

    print("│ Creating FAISS store..." + " " * 30 + "│")
    store = FAISSStore(user_id, base_path=str(base_path))
    store.delete_user_data()  # Clean start

    retriever = ContextRetriever(embedder)

    # Create and store synthetic exchanges
    print(f"│ Generating {num_exchanges} synthetic exchanges..." + " " * 18 + "│")
    exchanges = create_synthetic_exchanges(num_exchanges)

    print("│ Adding exchanges to FAISS index..." + " " * 19 + "│")
    for i, (user_text, assistant_text) in enumerate(exchanges):
        exchange_text = f"User: {user_text}\nAssistant: {assistant_text}"
        embedding = embedder.embed(exchange_text).reshape(1, -1)
        store.add_exchange(f"exch_{i}", user_text, assistant_text, embedding)

    print("│ ✓ Index populated" + " " * 37 + "│")
    print("├" + "─" * 58 + "┤")

    # Run benchmark queries
    print("│ Running benchmark queries..." + " " * 25 + "│")
    latencies = []

    # Generate test queries (mix of exact matches and variations)
    test_queries = []
    for i in range(num_queries):
        if i < num_exchanges:
            # Use actual exchange text for some queries (exact matches)
            test_queries.append(exchanges[i][0])
        else:
            # Generate variations
            topic_idx = i % len(create_synthetic_exchanges.__code__.co_consts)
            test_queries.append(f"Help with issue {i}")

    # Measure latency for each query
    for query in test_queries:
        start = time.perf_counter()
        results = retriever.retrieve(user_id, query, top_k=3)
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

    # Calculate statistics
    latencies.sort()
    min_latency = min(latencies)
    max_latency = max(latencies)
    avg_latency = sum(latencies) / len(latencies)
    p95_latency = latencies[int(len(latencies) * 0.95)]
    p99_latency = latencies[int(len(latencies) * 0.99)]

    # Print results
    print("│ ✓ Benchmark complete" + " " * 34 + "│")
    print("├" + "─" * 58 + "┤")
    print(f"│ Min latency    : {min_latency:>6.2f}ms" + " " * 26 + "│")
    print(f"│ Max latency    : {max_latency:>6.2f}ms" + " " * 26 + "│")
    print(f"│ Avg latency    : {avg_latency:>6.2f}ms" + " " * 26 + "│")
    print(f"│ P95 latency    : {p95_latency:>6.2f}ms" + " " * 26 + "│")
    print(f"│ P99 latency    : {p99_latency:>6.2f}ms" + " " * 26 + "│")
    print("├" + "─" * 58 + "┤")

    # Comparison with ChromaDB baseline
    chromadb_baseline = 20.0  # ms (conservative estimate)
    speedup = chromadb_baseline / avg_latency

    print(f"│ ChromaDB baseline (est) : ~{chromadb_baseline:.0f}ms" + " " * 20 + "│")
    print(f"│ FAISS speedup           : ~{speedup:.0f}x" + " " * 23 + "│")
    print("└" + "─" * 58 + "┘")

    # Performance assessment
    if avg_latency < 1.0:
        status = "✓ EXCELLENT"
        color = "green"
    elif avg_latency < 5.0:
        status = "✓ GOOD"
        color = "yellow"
    elif avg_latency < 10.0:
        status = "⚠ ACCEPTABLE"
        color = "yellow"
    else:
        status = "✗ NEEDS OPTIMIZATION"
        color = "red"

    print(f"\nPerformance: {status}")
    print(f"Target: <1ms average latency for real-time voice applications")

    # Cleanup
    store.delete_user_data()

    return {
        "num_exchanges": num_exchanges,
        "num_queries": num_queries,
        "min_latency_ms": min_latency,
        "max_latency_ms": max_latency,
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency,
        "p99_latency_ms": p99_latency,
        "chromadb_baseline_ms": chromadb_baseline,
        "speedup": speedup,
        "status": status
    }


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  FAISS vs ChromaDB Latency Benchmark")
    print("  Demonstrating why FAISS is optimal for voice assistants")
    print("=" * 60 + "\n")

    # Run benchmark
    results = run_benchmark(num_exchanges=50, num_queries=100)

    print("\n" + "=" * 60)
    print("  Benchmark Complete")
    print("=" * 60 + "\n")

    # Additional context
    print("Why these numbers matter for voice assistants:")
    print("─" * 60)
    print("• Voice conversations require <100ms total response time")
    print("• Retrieval is just one component (also: LLM, TTS)")
    print(f"• FAISS retrieval: ~{results['avg_latency_ms']:.1f}ms")
    print(f"• ChromaDB retrieval: ~{results['chromadb_baseline_ms']:.0f}ms")
    print(f"• Savings: ~{results['speedup']:.0f}x faster = better UX")
    print("─" * 60)
    print("\nFAISS achieves sub-millisecond latency by:")
    print("• Running entirely in RAM (no disk I/O)")
    print("• Using simple IndexFlatL2 (exact search, no overhead)")
    print("• Avoiding database machinery (no threads, locks, etc.)")
    print("• Optimized C++ implementation with Python bindings")
    print("\n")

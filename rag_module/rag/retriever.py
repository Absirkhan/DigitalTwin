"""
Context Retriever - Semantic Search for Past Conversations

This module implements semantic search over past conversation exchanges using
FAISS vector similarity. It retrieves relevant past exchanges to provide context
for the current conversation.

Key Features:
- Ranked retrieval by similarity score
- Threshold filtering to exclude irrelevant results
- Per-user FAISS store caching for performance
- Sub-millisecond retrieval latency
- Clean context formatting for prompt inclusion

The retriever works by:
1. Embedding the current user query
2. Searching the user's FAISS index for similar past exchanges
3. Ranking results by cosine similarity score
4. Filtering out low-relevance results
5. Formatting the context for inclusion in the LLM prompt
"""

import time
from typing import List, Dict
from pathlib import Path
from rag.embedder import EmbeddingEngine
from rag.faiss_store import FAISSStore


class ContextRetriever:
    """
    Retrieves relevant past conversation exchanges for context.

    The retriever maintains a cache of FAISSStore instances (one per user)
    to avoid repeatedly loading indexes from disk. When a user is accessed
    for the first time, their FAISS store is loaded and cached.

    All retrieval operations are ranked by cosine similarity, with higher
    scores indicating more relevant past exchanges.

    Attributes:
        embedder: EmbeddingEngine instance for query embedding
        stores: Dict mapping user_id to FAISSStore instances (cache)
    """

    def __init__(self, embedder: EmbeddingEngine):
        """
        Initialize the context retriever.

        Args:
            embedder: EmbeddingEngine instance for generating query embeddings
        """
        self.embedder = embedder
        self.stores = {}  # Cache of user_id -> FAISSStore

    def _get_store(self, user_id: str, base_path: str = "data/users") -> FAISSStore:
        """
        Get or create FAISSStore for a user.

        Stores are cached in self.stores to avoid repeatedly loading from disk.
        If a store doesn't exist in cache, it's loaded (or created) and cached.

        Note: The base_path parameter is only used when creating a new store.
        If a store is already cached for the user, it will be returned regardless
        of the base_path parameter. This is intentional for the test pattern where
        stores are manually injected.

        Args:
            user_id: User identifier
            base_path: Base directory for user data (only used for new stores)

        Returns:
            FAISSStore instance for the user
        """
        if user_id not in self.stores:
            self.stores[user_id] = FAISSStore(
                user_id=user_id,
                base_path=base_path,
                dimension=self.embedder.get_dimension()
            )
        return self.stores[user_id]

    def retrieve(
        self,
        user_id: str,
        query: str,
        top_k: int = 3,
        threshold: float = 0.0,
        base_path: str = "data/users"
    ) -> List[Dict]:
        """
        Retrieve top-k most relevant past exchanges for a query.

        The query is embedded and searched against the user's FAISS index.
        Results are ranked by cosine similarity score, with rank 1 being
        the most similar exchange.

        Args:
            user_id: User identifier
            query: Current user query/message
            top_k: Maximum number of results to return
            threshold: Minimum similarity score (0-1) to include in results
            base_path: Base directory for user data

        Returns:
            List of exchange dictionaries, each containing:
            - rank: Position in ranked results (1-based)
            - similarity_score: Cosine similarity (0-1, higher is better)
            - user_text: What the user said in the past exchange
            - assistant_text: How the assistant responded
            - timestamp: When the exchange occurred
            - All other fields from FAISSStore metadata

        Example:
            >>> retriever = ContextRetriever(embedder)
            >>> results = retriever.retrieve("user123", "error in my code", top_k=3)
            >>> for r in results:
            ...     print(f"Rank {r['rank']}: {r['similarity_score']:.3f} - {r['user_text']}")
        """
        # Get user's FAISS store
        store = self._get_store(user_id, base_path)

        # Handle empty store
        if store.get_total_exchanges() == 0:
            return []

        # Embed the query
        query_embedding = self.embedder.embed(query).reshape(1, -1)

        # Search FAISS index
        results = store.search(query_embedding, top_k=top_k)

        # Filter by threshold and add rank
        filtered_results = []
        rank = 1
        for result in results:
            if result['similarity_score'] >= threshold:
                result['rank'] = rank
                filtered_results.append(result)
                rank += 1

        return filtered_results

    def retrieve_above_threshold(
        self,
        user_id: str,
        query: str,
        threshold: float = 0.7,
        max_results: int = 3,
        base_path: str = "data/users"
    ) -> List[Dict]:
        """
        Retrieve only exchanges above a similarity threshold.

        This method is useful when you want to ensure all retrieved context
        is highly relevant. It will return fewer than max_results if there
        aren't enough high-similarity matches.

        Args:
            user_id: User identifier
            query: Current user query/message
            threshold: Minimum similarity score (0-1) to include
            max_results: Maximum number of results to return
            base_path: Base directory for user data

        Returns:
            List of exchange dictionaries (same format as retrieve())
            Only includes results with similarity_score >= threshold
        """
        # Use retrieve() with threshold filtering
        return self.retrieve(
            user_id=user_id,
            query=query,
            top_k=max_results,
            threshold=threshold,
            base_path=base_path
        )

    def format_context(self, results: List[Dict], max_results: int = 3) -> str:
        """
        Format retrieved exchanges into a clean context string.

        The formatted context is designed to be included in the LLM prompt,
        providing relevant past exchanges as context for the current query.

        Args:
            results: List of exchange dictionaries from retrieve()
            max_results: Maximum number of exchanges to include in formatted output

        Returns:
            Formatted context string, or empty string if no results

        Example output:
            [Past Exchange 1 - Similarity: 0.85]
            User: I have an error in my code
            Assistant: Let me help. What's the error message?

            [Past Exchange 2 - Similarity: 0.72]
            User: dimension mismatch error
            Assistant: Check your embedding shape.
        """
        if not results:
            return ""

        # Limit to max_results
        results = results[:max_results]

        formatted_parts = []
        for result in results:
            # Format header with rank and similarity
            header = f"[Past Exchange {result['rank']} - Similarity: {result['similarity_score']:.2f}]"

            # Format exchange text
            exchange_text = f"User: {result['user_text']}\nAssistant: {result['assistant_text']}"

            # Combine header and text
            formatted_parts.append(f"{header}\n{exchange_text}")

        # Join all exchanges with blank lines
        return "\n\n".join(formatted_parts)

    def measure_retrieval_latency(
        self,
        user_id: str,
        query: str,
        top_k: int = 3,
        base_path: str = "data/users"
    ) -> Dict:
        """
        Measure retrieval latency for benchmarking.

        This method is used for performance testing to ensure retrieval
        meets the sub-millisecond latency target.

        Args:
            user_id: User identifier
            query: Query to search for
            top_k: Number of results to retrieve
            base_path: Base directory for user data

        Returns:
            Dictionary containing:
            - latency_ms: Retrieval latency in milliseconds
            - results: Retrieved exchange dictionaries
            - num_results: Number of results returned

        Example:
            >>> data = retriever.measure_retrieval_latency("user123", "error")
            >>> print(f"Latency: {data['latency_ms']:.3f}ms")
            >>> print(f"Results: {data['num_results']}")
        """
        # Measure retrieval time
        start_time = time.perf_counter()
        results = self.retrieve(user_id, query, top_k=top_k, base_path=base_path)
        end_time = time.perf_counter()

        # Calculate latency in milliseconds
        latency_ms = (end_time - start_time) * 1000

        return {
            'latency_ms': latency_ms,
            'results': results,
            'num_results': len(results)
        }


# Example usage and testing
if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).parent.parent))

    from rag.embedder import EmbeddingEngine

    print("=== Context Retriever Test ===\n")

    # Initialize components
    embedder = EmbeddingEngine()
    retriever = ContextRetriever(embedder)

    user_id = "demo_retriever_user"
    base_path = str(Path(__file__).parent.parent / "data" / "users")

    # Get store and add test data
    store = retriever._get_store(user_id, base_path)
    store.delete_user_data()  # Clean start

    print("Adding test exchanges...")
    exchanges = [
        ("I have a bug in my code", "Let me help you debug it."),
        ("What is FAISS?", "FAISS is a similarity search library."),
        ("How do I fix errors?", "Check the error message first.")
    ]

    for i, (user_msg, asst_msg) in enumerate(exchanges):
        text = f"User: {user_msg}\nAssistant: {asst_msg}"
        emb = embedder.embed(text).reshape(1, -1)
        store.add_exchange(f"exch_{i}", user_msg, asst_msg, emb)

    print(f"[OK] Added {len(exchanges)} exchanges\n")

    # Test retrieval
    print("--- Retrieval Test ---")
    query = "error in my code"
    results = retriever.retrieve(user_id, query, top_k=3, base_path=base_path)

    print(f"Query: '{query}'")
    print(f"Retrieved {len(results)} results:\n")

    for r in results:
        print(f"Rank {r['rank']}: Score {r['similarity_score']:.3f}")
        print(f"  User: {r['user_text']}")
        print(f"  Assistant: {r['assistant_text']}")
        print()

    # Test formatting
    print("--- Format Context Test ---")
    formatted = retriever.format_context(results)
    print(formatted)
    print()

    # Test latency
    print("--- Latency Test ---")
    latency_data = retriever.measure_retrieval_latency(user_id, query, base_path=base_path)
    print(f"Latency: {latency_data['latency_ms']:.3f}ms")
    print(f"Results: {latency_data['num_results']}")
    print()

    # Cleanup
    store.delete_user_data()
    print("[OK] Test complete")

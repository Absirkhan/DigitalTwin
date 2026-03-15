"""
Embedding Engine - Text to Vector Conversion

This module handles all embedding generation using the sentence-transformers library.
The embedding model is loaded once at initialization and cached for efficient reuse.

Model Choice: all-MiniLM-L6-v2
- Lightweight: ~80MB model size
- Fast: Optimized for CPU inference
- Embedding dimension: 384 (compact representation)
- Well-suited for short conversational text similarity
- Balances quality and speed for real-time applications

L2 Normalization:
All embeddings are L2 normalized before being returned. This is critical because
FAISS IndexFlatL2 computes L2 distance, and for normalized vectors:
    L2 distance ≈ 2 * (1 - cosine similarity)
This means IndexFlatL2 on normalized vectors effectively performs cosine similarity
search, which is more appropriate for semantic text similarity than raw L2 distance.

Why CPU-Only:
This module is designed to run on CPU without any GPU dependencies, ensuring
maximum compatibility and deployment flexibility. The all-MiniLM-L6-v2 model
is specifically optimized for fast CPU inference.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Union


class EmbeddingEngine:
    """
    Handles text embedding generation using sentence-transformers.

    The embedding model is loaded once at initialization and reused for all
    subsequent embedding operations. This avoids the overhead of reloading
    the model for each embedding request.

    All embeddings are L2 normalized to ensure proper cosine similarity
    computation when used with FAISS IndexFlatL2.

    Attributes:
        model: SentenceTransformer model (all-MiniLM-L6-v2)
        dimension: Embedding vector dimension (384)
    """

    def __init__(self):
        """
        Initialize the embedding engine.

        Loads the all-MiniLM-L6-v2 model from sentence-transformers.
        This operation takes a few seconds on first run (model download),
        but subsequent runs load from cache instantly.

        The model is set to CPU mode explicitly to ensure no GPU dependencies.
        """
        print("Loading embedding model: all-MiniLM-L6-v2...")

        # Load model and force CPU mode
        self.model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')

        # The all-MiniLM-L6-v2 model produces 384-dimensional embeddings
        self.dimension = 384

        print(f"[OK] Embedding model loaded (dimension: {self.dimension})")

    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text string.

        The embedding is L2 normalized before returning, which ensures that
        when used with FAISS IndexFlatL2, the search effectively becomes
        cosine similarity search.

        Args:
            text: Input text string to embed

        Returns:
            Normalized embedding vector of shape (384,) as float32 numpy array

        Example:
            >>> engine = EmbeddingEngine()
            >>> embedding = engine.embed("Hello world")
            >>> embedding.shape
            (384,)
            >>> np.linalg.norm(embedding)  # Should be ~1.0 (normalized)
            1.0
        """
        # Generate embedding using the model
        embedding = self.model.encode(text, convert_to_numpy=True)

        # L2 normalize the embedding
        # This makes cosine similarity equivalent to L2 distance in FAISS
        embedding = embedding / np.linalg.norm(embedding)

        # Ensure float32 dtype for FAISS compatibility
        return embedding.astype(np.float32)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts in a single batch.

        This is more efficient than calling embed() in a loop because
        sentence-transformers can process multiple texts in parallel.
        All embeddings are L2 normalized.

        Args:
            texts: List of text strings to embed

        Returns:
            Normalized embedding matrix of shape (n, 384) as float32 numpy array
            where n is the number of input texts

        Example:
            >>> engine = EmbeddingEngine()
            >>> texts = ["Hello world", "How are you", "I am fine"]
            >>> embeddings = engine.embed_batch(texts)
            >>> embeddings.shape
            (3, 384)
        """
        if not texts:
            # Return empty array with correct shape if no texts provided
            return np.array([], dtype=np.float32).reshape(0, self.dimension)

        # Generate embeddings in batch
        embeddings = self.model.encode(texts, convert_to_numpy=True)

        # L2 normalize each embedding vector
        # Using axis=1 normalizes each row independently
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms

        # Ensure float32 dtype for FAISS compatibility
        return embeddings.astype(np.float32)

    def get_dimension(self) -> int:
        """
        Get the embedding dimension.

        Returns:
            Embedding vector dimension (384 for all-MiniLM-L6-v2)

        This method is used by FAISSStore during index initialization to ensure
        the index is created with the correct dimension.
        """
        return self.dimension


# Example usage and testing
if __name__ == "__main__":
    # Create embedding engine
    engine = EmbeddingEngine()

    # Test single embedding
    print("\n--- Single Embedding Test ---")
    text = "What is the error in my code?"
    embedding = engine.embed(text)
    print(f"Text: '{text}'")
    print(f"Embedding shape: {embedding.shape}")
    print(f"Embedding norm (should be ~1.0): {np.linalg.norm(embedding):.4f}")
    print(f"First 5 values: {embedding[:5]}")

    # Test batch embedding
    print("\n--- Batch Embedding Test ---")
    texts = [
        "Hello, how are you?",
        "I am having issues with my code",
        "The model is not loading properly"
    ]
    embeddings = engine.embed_batch(texts)
    print(f"Number of texts: {len(texts)}")
    print(f"Embeddings shape: {embeddings.shape}")
    print(f"All norms ~1.0: {[f'{np.linalg.norm(emb):.4f}' for emb in embeddings]}")

    # Test similarity
    print("\n--- Similarity Test ---")
    text1 = "I have a bug in my code"
    text2 = "There is an error in my program"
    text3 = "What is the weather today"

    emb1 = engine.embed(text1)
    emb2 = engine.embed(text2)
    emb3 = engine.embed(text3)

    # Cosine similarity = dot product for normalized vectors
    sim_1_2 = np.dot(emb1, emb2)
    sim_1_3 = np.dot(emb1, emb3)

    print(f"Similarity ('{text1}' vs '{text2}'): {sim_1_2:.4f}")
    print(f"Similarity ('{text1}' vs '{text3}'): {sim_1_3:.4f}")
    print(f"[OK] Similar texts have higher similarity score: {sim_1_2 > sim_1_3}")

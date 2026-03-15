"""
RAG Pipeline - Main Orchestrator

This module is the main entry point for the RAG system. It orchestrates all
components (embedding, retrieval, memory, profile, prompting) to provide
complete context-aware conversation support.

Key Features:
- User initialization with profile creation
- Message processing with context retrieval
- Exchange storage for long-term memory
- Session management (start/end)
- Token budget enforcement
- Sub-millisecond retrieval performance
- Per-user data isolation

Workflow:
1. initialize_user() - Set up user profile and FAISS store
2. process_message() - Retrieve context and build prompt for LLM
3. store_exchange() - Save conversation to long-term memory
4. end_session() - Clear session memory

The pipeline maintains separate short-term (session) and long-term (FAISS)
memory for optimal performance and context relevance.
"""

import time
from pathlib import Path
from typing import Dict, List
from rag.embedder import EmbeddingEngine
from rag.faiss_store import FAISSStore
from rag.retriever import ContextRetriever
from rag.memory_manager import SessionMemory
from rag.profile_manager import UserProfileManager
from rag.prompt_builder import PromptBuilder


class RAGPipeline:
    """
    Main RAG pipeline orchestrator.

    This class coordinates all RAG components to provide complete context-aware
    conversation support. It manages per-user state including FAISS indexes,
    session memory, and conversation profiles.

    The pipeline is designed for real-time voice assistant applications with
    strict latency requirements (<1ms retrieval).

    Attributes:
        base_path: Base directory for user data storage
        embedder: EmbeddingEngine instance
        retriever: ContextRetriever instance
        profile_manager: UserProfileManager instance
        prompt_builder: PromptBuilder instance
        session_memories: Dict of user_id -> SessionMemory instances
        faiss_stores: Dict of user_id -> FAISSStore instances
    """

    def __init__(self, base_path: str = "data/users"):
        """
        Initialize RAG pipeline.

        Loads all components and prepares for user sessions.

        Args:
            base_path: Base directory for user data storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        print("Initializing RAG Pipeline...")

        # Initialize components
        self.embedder = EmbeddingEngine()
        self.retriever = ContextRetriever(self.embedder)
        self.profile_manager = UserProfileManager(str(self.base_path))
        self.prompt_builder = PromptBuilder()

        # Per-user state
        self.session_memories = {}  # user_id -> SessionMemory
        self.faiss_stores = {}  # user_id -> FAISSStore (cache)

        print("[OK] RAG Pipeline initialized\n")

    def initialize_user(self, user_id: str) -> Dict:
        """
        Initialize or reinitialize a user session.

        This should be called at the start of each conversation session.
        It creates or loads the user's profile and FAISS store, and
        initializes a new session memory.

        Args:
            user_id: User identifier

        Returns:
            Dictionary containing:
            - user_id: User identifier
            - is_new_user: True if this is a new user (no existing data)
            - total_past_exchanges: Number of past exchanges stored
            - profile: User profile dictionary
            - session_initialized: True
        """
        # Create or load FAISS store
        if user_id not in self.faiss_stores:
            self.faiss_stores[user_id] = FAISSStore(
                user_id=user_id,
                base_path=str(self.base_path),
                dimension=self.embedder.get_dimension()
            )
            # Also cache in retriever
            self.retriever.stores[user_id] = self.faiss_stores[user_id]

        # Create or load profile
        is_new_user = not self.profile_manager.profile_exists(user_id)
        if is_new_user:
            profile = self.profile_manager.create_profile(user_id)
        else:
            profile = self.profile_manager.load_profile(user_id)

        # Initialize new session memory
        self.session_memories[user_id] = SessionMemory(max_messages=6)

        # Get total exchanges
        total_exchanges = self.faiss_stores[user_id].get_total_exchanges()

        return {
            "user_id": user_id,
            "is_new_user": is_new_user,
            "total_past_exchanges": total_exchanges,
            "profile": profile,
            "session_initialized": True
        }

    def process_message(self, user_id: str, message: str) -> Dict:
        """
        Process a user message and build prompt with context.

        This is the core method of the pipeline. It:
        1. Retrieves relevant past exchanges from FAISS
        2. Gets recent session history
        3. Gets user style summary
        4. Builds complete prompt with token budget enforcement
        5. Adds message to session memory

        Args:
            user_id: User identifier
            message: User message text

        Returns:
            Dictionary containing:
            - prompt: Complete prompt for LLM
            - retrieved_context: Retrieved past exchanges (formatted)
            - token_breakdown: Token count breakdown
            - retrieval_latency_ms: Time taken for retrieval (milliseconds)
            - num_results_retrieved: Number of past exchanges retrieved
        """
        # Ensure user is initialized
        if user_id not in self.session_memories:
            self.initialize_user(user_id)

        # Measure retrieval latency
        start_time = time.perf_counter()

        # Retrieve relevant past exchanges
        retrieval_results = self.retriever.retrieve(
            user_id=user_id,
            query=message,
            top_k=3,
            threshold=0.5,
            base_path=str(self.base_path)
        )

        retrieval_latency = (time.perf_counter() - start_time) * 1000  # ms

        # Format retrieved context
        retrieved_context = self.retriever.format_context(retrieval_results, max_results=3)

        # Get session history
        session_history = self.session_memories[user_id].format_for_prompt()

        # Get user style summary
        style_summary = ""
        if self.profile_manager.profile_exists(user_id):
            style_summary = self.profile_manager.get_style_summary(user_id)

        # Build prompt with all components
        prompt_result = self.prompt_builder.build_full_prompt(
            user_message=message,
            style_summary=style_summary,
            retrieved_context=retrieved_context,
            session_history=session_history
        )

        # Add user message to session memory
        self.session_memories[user_id].add_message("user", message)

        # Return complete result
        return {
            "prompt": prompt_result["prompt"],
            "retrieved_context": prompt_result["retrieved_context"],
            "token_breakdown": prompt_result["token_breakdown"],
            "retrieval_latency_ms": retrieval_latency,
            "num_results_retrieved": len(retrieval_results)
        }

    def store_exchange(self, user_id: str, user_message: str, assistant_response: str) -> None:
        """
        Store a conversation exchange in long-term memory.

        This adds the exchange to the user's FAISS index for future retrieval.
        It should be called after the assistant generates a response.

        Args:
            user_id: User identifier
            user_message: User's message
            assistant_response: Assistant's response
        """
        # Ensure user is initialized
        if user_id not in self.faiss_stores:
            self.initialize_user(user_id)

        # Create exchange text for embedding
        exchange_text = f"User: {user_message}\nAssistant: {assistant_response}"

        # Generate embedding
        embedding = self.embedder.embed(exchange_text).reshape(1, -1)

        # Generate exchange ID
        total_exchanges = self.faiss_stores[user_id].get_total_exchanges()
        exchange_id = f"exch_{total_exchanges}"

        # Add to FAISS store
        self.faiss_stores[user_id].add_exchange(
            exchange_id=exchange_id,
            user_text=user_message,
            assistant_text=assistant_response,
            embedding=embedding
        )

        # Add assistant response to session memory
        self.session_memories[user_id].add_message("assistant", assistant_response)

        # Update user profile with the new message
        self.profile_manager.update_profile(user_id, [user_message])

    def end_session(self, user_id: str) -> Dict:
        """
        End the current user session.

        Clears session memory while preserving long-term storage.
        The user's FAISS index and profile remain intact.

        Args:
            user_id: User identifier

        Returns:
            Dictionary containing:
            - session_cleared: True
            - messages_in_session: Number of messages cleared
            - total_exchanges_stored: Total exchanges in long-term memory
        """
        # Get session stats before clearing
        messages_in_session = 0
        if user_id in self.session_memories:
            messages_in_session = self.session_memories[user_id].get_message_count()
            self.session_memories[user_id].clear()

        # Get total exchanges
        total_exchanges = 0
        if user_id in self.faiss_stores:
            total_exchanges = self.faiss_stores[user_id].get_total_exchanges()

        return {
            "session_cleared": True,
            "messages_in_session": messages_in_session,
            "total_exchanges_stored": total_exchanges
        }

    def get_user_stats(self, user_id: str) -> Dict:
        """
        Get comprehensive statistics for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary containing:
            - user_id: User identifier
            - total_exchanges: Total exchanges in FAISS
            - session_messages: Current session message count
            - profile: User profile dictionary
        """
        # Get FAISS stats
        total_exchanges = 0
        if user_id in self.faiss_stores:
            total_exchanges = self.faiss_stores[user_id].get_total_exchanges()

        # Get session stats
        session_messages = 0
        if user_id in self.session_memories:
            session_messages = self.session_memories[user_id].get_message_count()

        # Get profile
        profile = None
        if self.profile_manager.profile_exists(user_id):
            profile = self.profile_manager.load_profile(user_id)

        return {
            "user_id": user_id,
            "total_exchanges": total_exchanges,
            "session_messages": session_messages,
            "profile": profile
        }


# Example usage and testing
if __name__ == "__main__":
    print("=== RAG Pipeline Test ===\n")

    # Initialize pipeline
    pipeline = RAGPipeline(base_path="../data/users")
    user_id = "demo_pipeline_user"

    # Clean start
    if user_id in pipeline.faiss_stores:
        pipeline.faiss_stores[user_id].delete_user_data()
    if pipeline.profile_manager.profile_exists(user_id):
        pipeline.profile_manager._get_profile_path(user_id).unlink()

    # Initialize user
    print("--- User Initialization ---")
    user_info = pipeline.initialize_user(user_id)
    print(f"New user: {user_info['is_new_user']}")
    print(f"Past exchanges: {user_info['total_past_exchanges']}")
    print()

    # Process messages and store exchanges
    print("--- Processing Messages ---")
    conversation = [
        ("I have an error in my code", "Let me help. What's the error?"),
        ("Dimension mismatch error", "Check your embedding shape."),
        ("How do I reshape it?", "Use .reshape(1, -1)")
    ]

    for i, (user_msg, asst_response) in enumerate(conversation, 1):
        print(f"Message {i}: {user_msg[:40]}...")

        # Process message
        result = pipeline.process_message(user_id, user_msg)

        print(f"  Retrieval latency: {result['retrieval_latency_ms']:.3f}ms")
        print(f"  Retrieved results: {result['num_results_retrieved']}")
        print(f"  Total tokens: {result['token_breakdown']['total']}")

        # Store exchange
        pipeline.store_exchange(user_id, user_msg, asst_response)
        print()

    # Get user stats
    print("--- User Statistics ---")
    stats = pipeline.get_user_stats(user_id)
    print(f"Total exchanges: {stats['total_exchanges']}")
    print(f"Session messages: {stats['session_messages']}")
    print()

    # End session
    print("--- Ending Session ---")
    session_stats = pipeline.end_session(user_id)
    print(f"Session cleared: {session_stats['session_cleared']}")
    print(f"Messages cleared: {session_stats['messages_in_session']}")
    print()

    # Reinitialize to test persistence
    print("--- Testing Persistence ---")
    user_info2 = pipeline.initialize_user(user_id)
    print(f"New user: {user_info2['is_new_user']}")
    print(f"Past exchanges: {user_info2['total_past_exchanges']}")
    print()

    # Cleanup
    pipeline.faiss_stores[user_id].delete_user_data()
    pipeline.profile_manager._get_profile_path(user_id).unlink()

    print("[OK] Test complete")

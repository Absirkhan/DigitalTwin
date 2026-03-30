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
from typing import Dict, List, Generator, Optional
from rag.embedder import EmbeddingEngine
from rag.faiss_store import FAISSStore
from rag.retriever import ContextRetriever
from rag.memory_manager import SessionMemory
from rag.profile_manager import UserProfileManager
from rag.prompt_builder import PromptBuilder

# Import LLM generator (optional - for response generation)
try:
    from rag.llm_generator import LLMGenerator
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


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

    def __init__(self, base_path: str = "data/users", enable_llm: bool = True):
        """
        Initialize RAG pipeline.

        Loads all components and prepares for user sessions.

        Args:
            base_path: Base directory for user data storage
            enable_llm: Whether to load LLM for response generation (default True)
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        print("Initializing RAG Pipeline...")

        # Initialize components
        self.embedder = EmbeddingEngine()
        self.retriever = ContextRetriever(self.embedder)
        self.profile_manager = UserProfileManager(str(self.base_path))
        self.prompt_builder = PromptBuilder()

        # Initialize LLM generator (optional)
        self.llm_generator = None
        if enable_llm and LLM_AVAILABLE:
            try:
                self.llm_generator = LLMGenerator(verbose=False)
                if self.llm_generator.model_loaded:
                    print("[OK] LLM generator loaded")
                else:
                    print("[WARN] LLM generator failed to load model")
                    self.llm_generator = None
            except Exception as e:
                print(f"[WARN] LLM generator unavailable: {e}")
                self.llm_generator = None
        elif enable_llm and not LLM_AVAILABLE:
            print("[WARN] LLM generator unavailable (llama-cpp-python not installed)")

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
            threshold=0.0,  # Accept all results, rely on top_k for limiting
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

    def generate_response(
        self,
        user_id: str,
        message: str,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
        auto_store: bool = True
    ) -> Dict:
        """
        Generate LLM response with RAG context (non-streaming).

        This is the main method for complete end-to-end response generation.
        It combines RAG context retrieval with LLM inference to produce
        context-aware responses.

        Flow:
        1. Retrieve relevant past exchanges (RAG)
        2. Build prompt with context
        3. Check LLM cache
        4. Generate response (or return cached)
        5. Optionally store exchange in long-term memory

        Args:
            user_id: User identifier
            message: User message text
            max_tokens: Maximum tokens to generate (default 200)
            use_cache: Whether to use LLM cache (default True)
            auto_store: Automatically store exchange after generation (default True)

        Returns:
            Dictionary containing:
            {
                "response": "Generated text...",
                "retrieval_latency_ms": 15.2,
                "llm_latency_ms": 3240.5,
                "total_latency_ms": 3255.7,
                "tokens_generated": 150,
                "cached": False,
                "token_breakdown": {...},
                "num_results_retrieved": 2
            }

        Raises:
            RuntimeError: If LLM generator is not available
        """
        if not self.llm_generator:
            raise RuntimeError(
                "LLM generator not available. "
                "Ensure llama-cpp-python is installed and model is downloaded."
            )

        # Get prompt with RAG context (using existing method)
        start_total = time.perf_counter()
        prompt_result = self.process_message(user_id, message)

        retrieval_latency_ms = prompt_result['retrieval_latency_ms']
        prompt = prompt_result['prompt']

        # Generate response with LLM
        start_llm = time.perf_counter()
        llm_result = self.llm_generator.generate_response(
            prompt=prompt,
            max_tokens=max_tokens,
            use_cache=use_cache
        )
        llm_latency_ms = (time.perf_counter() - start_llm) * 1000

        total_latency_ms = (time.perf_counter() - start_total) * 1000

        # Store exchange if requested
        if auto_store and llm_result.get('response'):
            self.store_exchange(user_id, message, llm_result['response'])

        # Return complete result
        return {
            "response": llm_result.get('response', ''),
            "retrieval_latency_ms": retrieval_latency_ms,
            "llm_latency_ms": llm_latency_ms,
            "total_latency_ms": total_latency_ms,
            "tokens_generated": llm_result.get('tokens_generated', 0),
            "cached": llm_result.get('cached', False),
            "cache_age_seconds": llm_result.get('cache_age_seconds', 0),
            "token_breakdown": prompt_result['token_breakdown'],
            "num_results_retrieved": prompt_result['num_results_retrieved']
        }

    def generate_response_stream(
        self,
        user_id: str,
        message: str,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
        auto_store: bool = True
    ) -> Generator[Dict, None, None]:
        """
        Generate LLM response with streaming (yields tokens as they generate).

        This method provides improved perceived latency by showing tokens
        as they're generated, rather than waiting for the full response.

        Args:
            user_id: User identifier
            message: User message text
            max_tokens: Maximum tokens to generate
            use_cache: Whether to use LLM cache
            auto_store: Automatically store exchange after generation

        Yields:
            Dictionaries with different event types:

            {"type": "context", "num_results": 2, "retrieval_latency_ms": 15.2}
            {"type": "token", "content": "Hello"}
            {"type": "token", "content": " world"}
            {"type": "done", "tokens_generated": 150, "latency_ms": 3240.5, "cached": False}
            {"type": "error", "error": "..."}

        Raises:
            RuntimeError: If LLM generator is not available
        """
        if not self.llm_generator:
            raise RuntimeError(
                "LLM generator not available. "
                "Ensure llama-cpp-python is installed and model is downloaded."
            )

        # Get prompt with RAG context
        start_total = time.perf_counter()
        prompt_result = self.process_message(user_id, message)

        # Yield context retrieval event
        yield {
            "type": "context",
            "num_results": prompt_result['num_results_retrieved'],
            "retrieval_latency_ms": prompt_result['retrieval_latency_ms'],
            "token_breakdown": prompt_result['token_breakdown']
        }

        prompt = prompt_result['prompt']
        full_response = ""

        # Stream LLM generation
        for chunk in self.llm_generator.generate_response_stream(
            prompt=prompt,
            max_tokens=max_tokens,
            use_cache=use_cache
        ):
            if chunk['type'] == 'token':
                full_response += chunk['content']

            yield chunk

        # Store exchange if requested and response was generated
        if auto_store and full_response:
            self.store_exchange(user_id, message, full_response.strip())

        # Calculate total latency
        total_latency_ms = (time.perf_counter() - start_total) * 1000

        # Yield final total latency
        yield {
            "type": "metadata",
            "total_latency_ms": total_latency_ms,
            "retrieval_latency_ms": prompt_result['retrieval_latency_ms']
        }

    def get_llm_cache_stats(self) -> Dict:
        """
        Get LLM cache statistics.

        Returns:
            Dictionary with cache hit rate, total queries, etc.
            Returns empty dict if LLM generator not available.
        """
        if self.llm_generator:
            return self.llm_generator.get_cache_stats()
        return {}

    def clear_llm_cache(self) -> int:
        """
        Clear LLM response cache.

        Returns:
            Number of cache entries cleared, or 0 if LLM not available
        """
        if self.llm_generator:
            return self.llm_generator.clear_cache()
        return 0

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
            - llm_cache_stats: LLM cache statistics (if available)
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

        # Get LLM cache stats
        llm_cache_stats = self.get_llm_cache_stats()

        return {
            "user_id": user_id,
            "total_exchanges": total_exchanges,
            "session_messages": session_messages,
            "profile": profile,
            "llm_cache_stats": llm_cache_stats
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

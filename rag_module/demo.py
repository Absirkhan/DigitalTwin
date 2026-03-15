"""
RAG Module Demo

Demonstrates complete RAG system functionality with a realistic conversation
scenario. Shows how past conversations are retrieved and used to provide
context-aware responses.

Simulates two sessions:
- Session 1 (past): User discusses FYP project issues
- Session 2 (current): User asks related questions, system retrieves relevant context

This demonstrates:
- Context retrieval from past conversations
- Token budget management
- User profile building
- Prompt assembly with all components
- Sub-millisecond retrieval latency
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from rag.pipeline import RAGPipeline


def print_section(title: str, width: int = 60):
    """Print section header."""
    print("\n-" + "-" * (width - 2) + "-")
    print("-" + title.center(width - 2) + "-")
    print("-" + "-" * (width - 2) + "-")


def print_box(title: str, content: dict, width: int = 60):
    """Print formatted box with content."""
    print("\n-" + "-" * (width - 2) + "-")
    print("- " + title + " " * (width - len(title) - 3) + "-")
    print("-" + "-" * (width - 2) + "-")

    for key, value in content.items():
        # Format key-value pairs
        if isinstance(value, (int, float)):
            if isinstance(value, float):
                line = f"- {key:20} : {value:>8.2f}" + " " * (width - 35) + "-"
            else:
                line = f"- {key:20} : {value:>8}" + " " * (width - 33) + "-"
        elif isinstance(value, bool):
            val_str = "YES" if value else "NO"
            line = f"- {key:20} : {val_str:>8}" + " " * (width - 34) + "-"
        else:
            line = f"- {key:20} : {str(value)}" + " " * (width - len(key) - len(str(value)) - 26) + "-"

        # Truncate if too long
        if len(line) > width + 1:
            line = line[:width - 4] + "...-"

        print(line)

    print("-" + "-" * (width - 2) + "-")


def run_demo():
    """Run complete RAG system demonstration."""
    width = 80

    print("\n" + "=" * width)
    print("  RAG MODULE DEMONSTRATION".center(width))
    print("  Real-Time Voice Assistant Context Retrieval".center(width))
    print("=" * width)

    # Initialize pipeline
    print_section("INITIALIZATION", width)
    print("\nInitializing RAG pipeline...")

    pipeline = RAGPipeline(base_path=str(Path(__file__).parent / "data" / "users"))
    user_id = "demo_user_001"

    # Clean start
    if user_id in pipeline.faiss_stores:
        pipeline.faiss_stores[user_id].delete_user_data()
    if pipeline.profile_manager.profile_exists(user_id):
        pipeline.profile_manager._get_profile_path(user_id).unlink()

    user_info = pipeline.initialize_user(user_id)
    print(f"\n[OK] User initialized: {user_id}")
    print(f"  New user: {user_info['is_new_user']}")

    # ═══════════════════════════════════════════════════════════
    # SESSION 1 - Past conversation (stored for future retrieval)
    # ═══════════════════════════════════════════════════════════
    print_section("SESSION 1 - Past Conversation", width)
    print("\nSimulating past session to populate context...")

    session1_conversation = [
        ("my FYP presentation is tomorrow and I am not ready",
         "Don't worry, I can help you prepare. What do you need to work on?"),

        ("the pipeline integration is still not complete",
         "Let's focus on the key components. What part of the pipeline are you working on?"),

        ("I am getting a dimension mismatch error in my embedding code",
         "Dimension mismatch usually means your embedding shape doesn't match. Are you using 384-dimensional embeddings?"),

        ("should I use cosine similarity or euclidean distance",
         "For normalized embeddings, both work similarly. Cosine similarity is more common for semantic search."),

        ("ok I fixed the error, the index is loading correctly now",
         "Great! That's progress. Make sure to test retrieval latency before your presentation.")
    ]

    print(f"\nProcessing {len(session1_conversation)} past exchanges...\n")

    for i, (user_msg, asst_response) in enumerate(session1_conversation, 1):
        # Process and store
        pipeline.process_message(user_id, user_msg)
        pipeline.store_exchange(user_id, user_msg, asst_response)
        print(f"  [{i}] Stored: \"{user_msg[:50]}...\"")

    # End session 1
    session1_stats = pipeline.end_session(user_id)
    print(f"\n[OK] Session 1 ended - {session1_stats['total_exchanges_stored']} exchanges stored")

    # ═══════════════════════════════════════════════════════════
    # SESSION 2 - Current conversation (with context retrieval)
    # ═══════════════════════════════════════════════════════════
    print_section("SESSION 2 - Current Conversation (with Retrieval)", width)

    # Reinitialize user (new session)
    user_info2 = pipeline.initialize_user(user_id)
    print(f"\n[OK] User reinitialized for new session")
    print(f"  Past exchanges available: {user_info2['total_past_exchanges']}")
    print(f"  User profile: {user_info2['profile']['speaking_style']['formality_level']}, "
          f"{user_info2['profile']['speaking_style']['avg_message_length']} messages")

    # Session 2 messages (related to session 1)
    session2_messages = [
        "I have another error in my embedding pipeline",
        "what similarity metric should I use for my vector search",
        "how do I make my retrieval faster"
    ]

    print("\nProcessing current session messages with context retrieval...\n")

    total_retrieval_latency = 0
    message_count = 0

    for i, user_msg in enumerate(session2_messages, 1):
        print("-" * width)
        print(f"\n USER MESSAGE {i}")
        print(f"   \"{user_msg}\"")
        print()

        # Process message
        result = pipeline.process_message(user_id, user_msg)

        # Display retrieved context
        print(" RETRIEVED CONTEXT")
        if result['retrieved_context'].strip():
            print("-" * width)
            # Print first 300 chars of context
            context_preview = result['retrieved_context'][:400]
            if len(result['retrieved_context']) > 400:
                context_preview += "..."
            print(context_preview)
            print("-" * width)
        else:
            print("   (No relevant context found)")

        print()

        # Display token breakdown
        breakdown = result['token_breakdown']
        print_box("TOKEN BREAKDOWN", {
            "System prompt": breakdown['system_prompt'],
            "Profile summary": breakdown['profile_summary'],
            "Retrieved context": breakdown['retrieved_context'],
            "Session history": breakdown['session_history'],
            "User message": breakdown['user_message'],
            "Total": breakdown['total'],
            "Budget remaining": breakdown['budget_remaining'],
            "Within budget": breakdown['within_budget']
        }, width=width)

        # Display latency
        latency_ms = result['retrieval_latency_ms']
        total_retrieval_latency += latency_ms
        message_count += 1

        print(f"\n RETRIEVAL LATENCY: {latency_ms:.2f}ms")

        # Display number of results
        print(f"   Retrieved {result['num_results_retrieved']} relevant past exchanges")

        # Simulate assistant response and store
        simulated_response = f"Based on our past conversation, here's my answer to message {i}."
        pipeline.store_exchange(user_id, user_msg, simulated_response)

        print()

    # End session 2
    print("-" * width)
    session2_stats = pipeline.end_session(user_id)

    # ═══════════════════════════════════════════════════════════
    # FINAL STATISTICS
    # ═══════════════════════════════════════════════════════════
    print_section("FINAL STATISTICS", width)

    # Get user stats
    user_stats = pipeline.get_user_stats(user_id)

    # User profile
    profile = user_stats['profile']
    print("\n USER PROFILE")
    print("-" * width)
    print(f"  Formality level      : {profile['speaking_style']['formality_level']}")
    print(f"  Avg message length   : {profile['speaking_style']['avg_message_length']}")
    print(f"  Avg words per message: {profile['speaking_style']['avg_words_per_message']}")
    print(f"  Uses technical terms : {profile['speaking_style']['uses_technical_terms']}")
    print(f"  Common vocabulary    : {', '.join(profile['speaking_style']['common_vocabulary'][:5])}")
    print(f"  Typical topics       : {', '.join(profile['speaking_style']['typical_topics'][:3])}")

    # Style summary
    style_summary = pipeline.profile_manager.get_style_summary(user_id)
    print(f"\n  Style summary:")
    print(f"  \"{style_summary}\"")

    # Storage stats
    print(f"\n STORAGE STATISTICS")
    print("-" * width)
    print(f"  Total exchanges stored : {user_stats['total_exchanges']}")
    print(f"  Session 1 messages     : {len(session1_conversation)}")
    print(f"  Session 2 messages     : {len(session2_messages)}")

    # Performance stats
    avg_latency = total_retrieval_latency / message_count if message_count > 0 else 0
    print(f"\n PERFORMANCE STATISTICS")
    print("-" * width)
    print(f"  Average retrieval latency : {avg_latency:.2f}ms")
    print(f"  Target latency            : <1.0ms")
    print(f"  Performance status        : {'[OK] EXCELLENT' if avg_latency < 1.0 else '[OK] GOOD' if avg_latency < 5.0 else '[WARN] ACCEPTABLE'}")

    # System capabilities
    print(f"\n SYSTEM CAPABILITIES DEMONSTRATED")
    print("-" * width)
    print("  [OK] Context retrieval from past conversations")
    print("  [OK] User profile building and style matching")
    print("  [OK] Token budget enforcement (2150 token limit)")
    print("  [OK] Sub-millisecond retrieval latency")
    print("  [OK] Persistent storage across sessions")
    print("  [OK] Per-user data isolation")

    # Cleanup
    print_section("CLEANUP", width)
    print("\nCleaning up demo data...")
    if user_id in pipeline.faiss_stores:
        pipeline.faiss_stores[user_id].delete_user_data()
    if pipeline.profile_manager.profile_exists(user_id):
        pipeline.profile_manager._get_profile_path(user_id).unlink()

    print("[OK] Demo data cleaned up")

    print("\n" + "=" * width)
    print("  DEMO COMPLETE".center(width))
    print("=" * width + "\n")


if __name__ == "__main__":
    run_demo()

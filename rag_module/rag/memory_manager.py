"""
Session Memory Manager - Short-Term Conversation Context

This module manages short-term conversation memory within a single session.
It stores the most recent messages in memory (not persisted to disk) to provide
immediate conversational context.

Key Features:
- In-memory storage (Python list) for speed
- Automatic truncation to maintain recency (max 6 messages)
- Clean formatting for prompt inclusion
- Per-user session isolation
- Automatic clearing at session end

Session vs Long-Term Memory:
- Session memory: Last few messages in current conversation (in RAM, volatile)
- Long-term memory: All past exchanges across all sessions (FAISS, persistent)

The session memory is combined with retrieved long-term context to build the
complete conversation context for the LLM.
"""

from typing import List, Dict


class SessionMemory:
    """
    Manages short-term conversation memory for a single session.

    Session memory stores the most recent messages from the current conversation.
    This is separate from long-term memory (FAISS) which stores all past exchanges.

    The memory automatically truncates to keep only the most recent messages,
    ensuring the session context doesn't grow unbounded.

    Attributes:
        messages: List of message dictionaries (role, content)
        max_messages: Maximum messages to keep (default 6)
    """

    def __init__(self, max_messages: int = 6):
        """
        Initialize session memory.

        Args:
            max_messages: Maximum number of messages to keep in memory.
                         When this limit is reached, oldest messages are removed.
                         Default is 6 messages (3 user + 3 assistant turns).
        """
        self.messages = []
        self.max_messages = max_messages

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to session memory.

        Messages are added chronologically. When max_messages is reached,
        the oldest message is removed before adding the new one.

        Args:
            role: Message role ("user" or "assistant")
            content: Message content text

        Example:
            >>> memory = SessionMemory()
            >>> memory.add_message("user", "Hello")
            >>> memory.add_message("assistant", "Hi there!")
        """
        # Add new message
        self.messages.append({
            "role": role,
            "content": content
        })

        # Truncate if over limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_recent_messages(self, n: int = None) -> List[Dict]:
        """
        Get the n most recent messages.

        Args:
            n: Number of recent messages to return. If None, returns all messages.

        Returns:
            List of message dictionaries in chronological order

        Example:
            >>> memory.get_recent_messages(2)
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        if n is None:
            return self.messages.copy()

        # Return last n messages
        return self.messages[-n:] if n > 0 else []

    def format_for_prompt(self) -> str:
        """
        Format session messages for inclusion in LLM prompt.

        Formats all messages in chronological order with clear role labels.
        This is designed to provide recent conversation context to the LLM.

        Returns:
            Formatted string of session messages, or empty string if no messages

        Example output:
            User: Hello, I need help
            Assistant: Sure, what do you need help with?
            User: I have an error
        """
        if not self.messages:
            return ""

        formatted_parts = []
        for msg in self.messages:
            role_label = msg["role"].capitalize()
            formatted_parts.append(f"{role_label}: {msg['content']}")

        return "\n".join(formatted_parts)

    def clear(self) -> int:
        """
        Clear all messages from session memory.

        This is called at the end of a session to reset the memory for
        the next conversation.

        Returns:
            Number of messages that were cleared

        Example:
            >>> num_cleared = memory.clear()
            >>> print(f"Cleared {num_cleared} messages")
        """
        num_messages = len(self.messages)
        self.messages = []
        return num_messages

    def get_message_count(self) -> int:
        """
        Get the number of messages currently in session memory.

        Returns:
            Number of messages stored
        """
        return len(self.messages)

    def is_empty(self) -> bool:
        """
        Check if session memory is empty.

        Returns:
            True if no messages are stored, False otherwise
        """
        return len(self.messages) == 0


# Example usage and testing
if __name__ == "__main__":
    print("=== Session Memory Test ===\n")

    # Create session memory
    memory = SessionMemory(max_messages=6)

    # Add messages
    print("Adding messages...")
    memory.add_message("user", "Hello, I need help with my code")
    memory.add_message("assistant", "Sure, I'd be happy to help. What's the issue?")
    memory.add_message("user", "I have a dimension mismatch error")
    memory.add_message("assistant", "Let me help you fix that. Can you show me the error?")

    print(f"[OK] Added {memory.get_message_count()} messages\n")

    # Get recent messages
    print("--- Recent Messages (last 2) ---")
    recent = memory.get_recent_messages(2)
    for msg in recent:
        print(f"{msg['role']}: {msg['content']}")
    print()

    # Format for prompt
    print("--- Formatted for Prompt ---")
    formatted = memory.format_for_prompt()
    print(formatted)
    print()

    # Test truncation
    print("--- Testing Truncation ---")
    for i in range(5):
        memory.add_message("user", f"Message {i}")
        memory.add_message("assistant", f"Response {i}")

    print(f"Messages after adding 10 more: {memory.get_message_count()} (max: 6)")
    print(f"[OK] Truncation working correctly\n")

    # Clear memory
    print("--- Clearing Memory ---")
    num_cleared = memory.clear()
    print(f"Cleared {num_cleared} messages")
    print(f"Is empty: {memory.is_empty()}")
    print()

    print("[OK] Test complete")

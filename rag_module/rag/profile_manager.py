"""
User Profile Manager - Conversational Style Learning

This module learns and maintains user-specific conversational profiles by analyzing
their message patterns. Profiles are used to generate style summaries that help
the assistant match the user's communication preferences.

Key Features:
- Automatic profile creation and updates
- Speaking style analysis (formality, message length, vocabulary)
- Technical term detection
- Topic extraction
- Persistent storage as JSON files
- Concise style summaries for prompt inclusion

Profile Structure:
- user_id: User identifier
- created_at: Profile creation timestamp
- speaking_style:
  - formality_level: "casual" or "formal"
  - avg_message_length: "short", "medium", or "long"
  - avg_words_per_message: Numeric average
  - uses_technical_terms: Boolean
  - common_vocabulary: List of frequent words
  - typical_topics: List of common topics
- conversation_stats:
  - total_messages: Total number of user messages analyzed
"""

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from collections import Counter


class UserProfileManager:
    """
    Manages user conversation profiles for personalized responses.

    Each user gets a profile that learns their communication style over time.
    The profile is updated incrementally as new messages are analyzed.

    Profiles are stored as JSON files in {base_path}/{user_id}/profile.json

    Attributes:
        base_path: Base directory for user data storage
    """

    def __init__(self, base_path: str):
        """
        Initialize profile manager.

        Args:
            base_path: Base directory for user data (e.g., "data/users")
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_profile_path(self, user_id: str) -> Path:
        """
        Get path to user's profile file.

        Args:
            user_id: User identifier

        Returns:
            Path to profile.json file
        """
        user_dir = self.base_path / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / "profile.json"

    def profile_exists(self, user_id: str) -> bool:
        """
        Check if a user profile exists.

        Args:
            user_id: User identifier

        Returns:
            True if profile file exists, False otherwise
        """
        return self._get_profile_path(user_id).exists()

    def create_profile(self, user_id: str) -> Dict:
        """
        Create a new user profile with default values.

        Args:
            user_id: User identifier

        Returns:
            New profile dictionary with default values
        """
        profile = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "speaking_style": {
                "formality_level": "casual",  # Default to casual
                "avg_message_length": "short",  # Default to short
                "avg_words_per_message": 0.0,
                "uses_technical_terms": False,
                "common_vocabulary": [],
                "typical_topics": []
            },
            "conversation_stats": {
                "total_messages": 0
            }
        }

        # Save to disk
        profile_path = self._get_profile_path(user_id)
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

        return profile

    def load_profile(self, user_id: str) -> Dict:
        """
        Load user profile from disk.

        Args:
            user_id: User identifier

        Returns:
            Profile dictionary

        Raises:
            FileNotFoundError: If profile doesn't exist
        """
        profile_path = self._get_profile_path(user_id)

        if not profile_path.exists():
            raise FileNotFoundError(f"Profile not found for user {user_id}")

        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def update_profile(self, user_id: str, messages: List[str]) -> Dict:
        """
        Update user profile by analyzing new messages.

        This method analyzes the provided messages and updates the user's
        profile with learned patterns. It computes:
        - Average message length and word count
        - Formality level (based on punctuation and capitalization)
        - Technical term usage
        - Common vocabulary
        - Typical topics

        Args:
            user_id: User identifier
            messages: List of user message strings to analyze

        Returns:
            Updated profile dictionary
        """
        # Load or create profile
        if self.profile_exists(user_id):
            profile = self.load_profile(user_id)
        else:
            profile = self.create_profile(user_id)

        # Analyze messages
        if not messages:
            return profile

        # Calculate statistics
        total_words = 0
        total_chars = 0
        all_words = []
        formal_indicators = 0
        technical_terms_found = set()

        # Common technical terms to detect
        tech_terms = {
            'error', 'bug', 'code', 'function', 'model', 'training', 'database',
            'api', 'server', 'client', 'python', 'neural', 'network', 'algorithm',
            'data', 'query', 'latency', 'optimization', 'dimension', 'embedding',
            'vector', 'index', 'faiss', 'ml', 'ai', 'learning', 'tensorflow',
            'pytorch', 'numpy', 'pandas', 'sql', 'json', 'http', 'rest'
        }

        for msg in messages:
            # Word count
            words = msg.lower().split()
            total_words += len(words)
            total_chars += len(msg)
            all_words.extend(words)

            # Formality detection (simple heuristic)
            if msg[0].isupper() if msg else False:
                formal_indicators += 1
            if msg.endswith('.') or msg.endswith('!') or msg.endswith('?'):
                formal_indicators += 1

            # Technical term detection
            for word in words:
                # Clean punctuation
                clean_word = word.strip('.,!?;:')
                if clean_word in tech_terms:
                    technical_terms_found.add(clean_word)

        # Update statistics
        num_messages = len(messages)
        avg_words = total_words / num_messages if num_messages > 0 else 0
        avg_chars = total_chars / num_messages if num_messages > 0 else 0

        # Determine message length category
        if avg_words < 5:
            avg_length = "short"
        elif avg_words < 15:
            avg_length = "medium"
        else:
            avg_length = "long"

        # Determine formality
        formality_ratio = formal_indicators / (num_messages * 2) if num_messages > 0 else 0
        formality = "formal" if formality_ratio > 0.6 else "casual"

        # Get common vocabulary (top 10 most frequent words, excluding common words)
        stop_words = {'i', 'a', 'the', 'is', 'are', 'was', 'were', 'to', 'of', 'and',
                      'in', 'my', 'have', 'has', 'do', 'does', 'it', 'that', 'this'}
        word_counts = Counter([w for w in all_words if w not in stop_words and len(w) > 2])
        common_vocab = [word for word, count in word_counts.most_common(10)]

        # Extract typical topics (based on most common content words)
        topic_words = {'error', 'code', 'model', 'training', 'data', 'network',
                       'database', 'api', 'server', 'function', 'learning', 'neural'}
        topics = [word for word in common_vocab if word in topic_words]
        if not topics:
            topics = common_vocab[:3]  # Use top 3 words as topics if no topic words found

        # Update profile
        old_total = profile['conversation_stats']['total_messages']
        new_total = old_total + num_messages

        # Weighted average with previous stats
        if old_total > 0:
            old_avg = profile['speaking_style']['avg_words_per_message']
            profile['speaking_style']['avg_words_per_message'] = \
                (old_avg * old_total + avg_words * num_messages) / new_total
        else:
            profile['speaking_style']['avg_words_per_message'] = avg_words

        profile['speaking_style']['avg_message_length'] = avg_length
        profile['speaking_style']['formality_level'] = formality
        profile['speaking_style']['uses_technical_terms'] = len(technical_terms_found) > 0
        profile['speaking_style']['common_vocabulary'] = common_vocab
        profile['speaking_style']['typical_topics'] = topics
        profile['conversation_stats']['total_messages'] = new_total

        # Save updated profile
        profile_path = self._get_profile_path(user_id)
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

        return profile

    def get_style_summary(self, user_id: str) -> str:
        """
        Generate a concise style summary for prompt inclusion.

        The summary is a brief description of the user's communication style,
        designed to help the LLM match the user's preferences.

        Args:
            user_id: User identifier

        Returns:
            Concise style summary string (under 200 words)

        Example:
            "User speaks casually with short messages (avg 8 words). Uses technical
            terms related to code, errors, and models. Common topics: debugging,
            machine learning, API development."
        """
        if not self.profile_exists(user_id):
            return "User has no conversation history yet. Speak in a friendly, helpful manner."

        profile = self.load_profile(user_id)
        style = profile['speaking_style']

        # Build summary
        formality = style['formality_level']
        length = style['avg_message_length']
        avg_words = int(style['avg_words_per_message'])
        uses_tech = style['uses_technical_terms']
        topics = style['typical_topics'][:3] if style['typical_topics'] else []

        summary_parts = []

        # Formality and length
        summary_parts.append(f"User speaks {formality}ly with {length} messages")
        if avg_words > 0:
            summary_parts[-1] += f" (avg {avg_words} words)"
        summary_parts[-1] += "."

        # Technical terms
        if uses_tech:
            summary_parts.append("Uses technical terms.")

        # Topics
        if topics:
            topics_str = ", ".join(topics)
            summary_parts.append(f"Common topics: {topics_str}.")

        # General guidance
        if formality == "formal":
            summary_parts.append("Match their formal tone and provide detailed explanations.")
        else:
            summary_parts.append("Keep responses casual and concise.")

        return " ".join(summary_parts)


# Example usage and testing
if __name__ == "__main__":
    print("=== User Profile Manager Test ===\n")

    # Initialize manager
    manager = UserProfileManager(base_path="../data/users")
    user_id = "demo_profile_user"

    # Clean start
    if manager.profile_exists(user_id):
        manager._get_profile_path(user_id).unlink()

    # Create profile
    print("Creating new profile...")
    profile = manager.create_profile(user_id)
    print(f"[OK] Profile created for {user_id}\n")

    # Update profile with messages
    print("Updating profile with messages...")
    messages = [
        "I have an error in my Python code",
        "The neural network model is not training properly",
        "How do I optimize the database query latency",
        "The embedding dimension is causing issues"
    ]

    updated_profile = manager.update_profile(user_id, messages)
    print(f"[OK] Profile updated with {len(messages)} messages\n")

    # Display profile
    print("--- Profile Summary ---")
    print(f"Formality: {updated_profile['speaking_style']['formality_level']}")
    print(f"Avg message length: {updated_profile['speaking_style']['avg_message_length']}")
    print(f"Avg words/message: {updated_profile['speaking_style']['avg_words_per_message']:.1f}")
    print(f"Uses technical terms: {updated_profile['speaking_style']['uses_technical_terms']}")
    print(f"Common vocabulary: {', '.join(updated_profile['speaking_style']['common_vocabulary'][:5])}")
    print(f"Typical topics: {', '.join(updated_profile['speaking_style']['typical_topics'])}")
    print()

    # Get style summary
    print("--- Style Summary ---")
    summary = manager.get_style_summary(user_id)
    print(summary)
    print()

    # Cleanup
    manager._get_profile_path(user_id).unlink()
    print("[OK] Test complete")

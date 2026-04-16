"""
Bot Speaking Decision Engine

Determines when the bot should respond in meetings based on direct address detection.
Only responds when explicitly addressed by name (e.g., "Hey BotName, ...").

NO automatic responses to questions or keywords - only direct address.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class BotSpeakingEngine:
    """
    Engine for detecting when bot should speak in a meeting.

    Implements direct address detection with multiple patterns:
    - "Hey BotName, can you help?"
    - "BotName, what do you think?"
    - "@BotName please explain"
    - "I have a question. BotName, can you answer?"
    """

    def __init__(self):
        """Initialize the bot speaking engine."""
        logger.info("Bot Speaking Engine initialized")

    def is_directly_addressed(self, text: str, bot_name: str) -> bool:
        """
        Check if the text directly addresses the bot by name.

        Args:
            text: The transcript text to analyze
            bot_name: The name of the bot to check for

        Returns:
            True if bot is directly addressed, False otherwise

        Examples:
            >>> engine.is_directly_addressed("Hey Digital Twin, can you help?", "Digital Twin")
            True
            >>> engine.is_directly_addressed("What do you think about this?", "Digital Twin")
            False
            >>> engine.is_directly_addressed("I agree. Digital Twin, what's your opinion?", "Digital Twin")
            True
        """
        if not text or not bot_name:
            return False

        text_lower = text.lower().strip()
        name_lower = bot_name.lower().strip()

        # Pattern 1: Starts with bot name (with optional greeting prefix)
        prefixes = ["hey", "hi", "hello", "yo", "@", "okay", "ok"]
        for prefix in prefixes:
            pattern = f"{prefix} {name_lower}"
            if text_lower.startswith(pattern):
                logger.debug(f"Direct address detected: prefix pattern '{pattern}'")
                return True

        # Pattern 2: Starts directly with bot name
        if text_lower.startswith(name_lower):
            # Make sure it's followed by punctuation or space
            if len(text_lower) > len(name_lower):
                next_char = text_lower[len(name_lower)]
                if next_char in [',', ':', ' ', '?', '!', '.']:
                    logger.debug(f"Direct address detected: starts with bot name")
                    return True

        # Pattern 3: After sentence punctuation (new sentence addressing bot)
        patterns = [
            f". {name_lower},",
            f". {name_lower} ",
            f"! {name_lower},",
            f"! {name_lower} ",
            f"? {name_lower},",
            f"? {name_lower} ",
        ]

        for pattern in patterns:
            if pattern in text_lower:
                logger.debug(f"Direct address detected: after punctuation '{pattern}'")
                return True

        # Pattern 4: @ mention anywhere in text
        at_mention = f"@{name_lower}"
        if at_mention in text_lower:
            logger.debug(f"Direct address detected: @ mention")
            return True

        # Pattern 5: Bot name at END of sentence (questions)
        # Examples: "What database are you using Bot?", "Can you help Bot?"
        end_patterns = [
            f" {name_lower}?",
            f" {name_lower}.",
            f" {name_lower}!",
        ]

        for pattern in end_patterns:
            if text_lower.endswith(pattern):
                logger.debug(f"Direct address detected: bot name at end '{pattern}'")
                return True

        return False

    def is_speaker_bot(self, speaker_name: str, bot_name: str) -> bool:
        """
        Check if the speaker is the bot itself (avoid self-response loop).

        Args:
            speaker_name: Name of the current speaker
            bot_name: Name of the bot

        Returns:
            True if speaker is the bot, False otherwise
        """
        if not speaker_name or not bot_name:
            return False

        speaker_lower = speaker_name.lower().strip()
        bot_lower = bot_name.lower().strip()

        # Check if speaker matches bot name
        if speaker_lower == bot_lower:
            return True

        # Recall.ai often shows bot as "Unknown" speaker
        if speaker_lower == "unknown":
            return True

        return False

    def extract_query_from_address(self, text: str, bot_name: str) -> str:
        """
        Remove bot name and addressing words from the query.

        Args:
            text: The full transcript text
            bot_name: The bot name to remove

        Returns:
            Cleaned query text without addressing patterns

        Examples:
            >>> engine.extract_query_from_address("Hey Digital Twin, can you help?", "Digital Twin")
            "can you help?"
            >>> engine.extract_query_from_address("@Digital Twin what's the status?", "Digital Twin")
            "what's the status?"
        """
        text_cleaned = text.strip()

        # Remove common addressing patterns (case-insensitive)
        patterns_to_remove = [
            f"Hey {bot_name},",
            f"Hey {bot_name} ",
            f"Hi {bot_name},",
            f"Hi {bot_name} ",
            f"Hello {bot_name},",
            f"Hello {bot_name} ",
            f"{bot_name},",
            f"{bot_name} ",
            f"@{bot_name}",
            f"Yo {bot_name},",
            f"Okay {bot_name},",
            f"Ok {bot_name},",
        ]

        for pattern in patterns_to_remove:
            # Case-insensitive replacement
            text_cleaned = re.sub(
                re.escape(pattern),
                "",
                text_cleaned,
                count=1,
                flags=re.IGNORECASE
            )

        # Remove bot name from END of sentence (e.g., "What database are you using Bot?")
        text_lower_check = text_cleaned.lower().strip()
        name_lower = bot_name.lower().strip()

        end_patterns = [
            f" {name_lower}?",
            f" {name_lower}.",
            f" {name_lower}!",
        ]

        for end_pattern in end_patterns:
            if text_lower_check.endswith(end_pattern):
                # Remove " {name}" from end but keep punctuation
                # Example: "Hello Bot?" -> remove " Bot" (4 chars), keep "?"
                # Pattern: " bot?" (5 chars total)

                # Get the punctuation mark (last char of original text)
                punctuation = text_cleaned[-1]

                # Remove the entire pattern including punctuation
                text_cleaned = text_cleaned[:-len(end_pattern)]

                # Add back just the punctuation (no space before it)
                text_cleaned = text_cleaned.rstrip() + punctuation
                break

        # Clean up extra whitespace and punctuation at start
        text_cleaned = text_cleaned.strip()
        if text_cleaned.startswith((',', ':', '-')):
            text_cleaned = text_cleaned[1:].strip()

        logger.debug(f"Extracted query: '{text_cleaned}' from '{text}'")

        return text_cleaned if text_cleaned else text

    def should_respond(
        self,
        text: str,
        speaker_name: str,
        bot_name: str
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if bot should respond to this transcript chunk.

        Args:
            text: Transcript text to analyze
            speaker_name: Name of the speaker
            bot_name: Name of the bot

        Returns:
            Tuple of (should_respond: bool, reason: str)
            reason is None if should_respond is True, otherwise explains why not

        Examples:
            >>> engine.should_respond("Hey Bot, help me", "John", "Bot")
            (True, None)
            >>> engine.should_respond("I think we should...", "John", "Bot")
            (False, "Not directly addressed")
            >>> engine.should_respond("Hey Bot, help me", "Bot", "Bot")
            (False, "Speaker is bot itself")
        """
        # Check 1: Is speaker the bot itself?
        if self.is_speaker_bot(speaker_name, bot_name):
            return False, "Speaker is bot itself"

        # Check 2: Is bot directly addressed?
        if not self.is_directly_addressed(text, bot_name):
            return False, "Not directly addressed"

        # All checks passed
        logger.info(
            f"Bot should respond: speaker='{speaker_name}', "
            f"bot='{bot_name}', text='{text[:50]}...'"
        )
        return True, None


# Singleton instance
_bot_speaking_engine: Optional[BotSpeakingEngine] = None


def get_bot_speaking_engine() -> BotSpeakingEngine:
    """
    Get the global BotSpeakingEngine instance.

    Returns:
        BotSpeakingEngine: Singleton instance
    """
    global _bot_speaking_engine

    if _bot_speaking_engine is None:
        _bot_speaking_engine = BotSpeakingEngine()

    return _bot_speaking_engine


# Example usage and testing
if __name__ == "__main__":
    print("=== Bot Speaking Engine Test ===\n")

    engine = BotSpeakingEngine()
    bot_name = "Digital Twin"

    test_cases = [
        ("Hey Digital Twin, can you help?", "John", True),
        ("What do you think about this?", "John", False),
        ("I agree. Digital Twin, what's your opinion?", "Sarah", True),
        ("@Digital Twin please explain", "Mike", True),
        ("Digital Twin, are you there?", "Alice", True),
        ("The digital twin system is great", "Bob", False),
        ("Hey Digital Twin, test", "Digital Twin", False),  # Bot speaking to itself
        ("digital twin, help me", "John", True),  # Case insensitive
        ("DIGITAL TWIN, HELLO", "John", True),  # All caps
    ]

    print(f"Testing with bot name: '{bot_name}'\n")

    for text, speaker, expected in test_cases:
        should_respond, reason = engine.should_respond(text, speaker, bot_name)

        status = "[OK]" if should_respond == expected else "[FAIL]"
        print(f"{status} Text: '{text[:40]}...'")
        print(f"     Speaker: {speaker}")
        print(f"     Expected: {expected}, Got: {should_respond}")
        if reason:
            print(f"     Reason: {reason}")

        if should_respond:
            query = engine.extract_query_from_address(text, bot_name)
            print(f"     Extracted query: '{query}'")

        print()

    print("[OK] Test complete")

"""
Prompt Builder - LLM Prompt Assembly with Token Management

This module builds prompts for the LLM by combining all context components
and managing the token budget to stay within model limits.

Key Features:
- Token counting with offline fallback (tiktoken with word-based estimation)
- Token budget enforcement (2150 tokens total, 1650 for prompt)
- Component-wise token tracking (system, profile, context, history, message)
- Clean prompt assembly
- Budget overflow handling

Token Budget (2150 total):
- System prompt: ~100-200 tokens
- Profile summary: ~50-100 tokens
- Retrieved context: Variable (automatically truncated)
- Session history: Variable (automatically truncated)
- User message: Variable
- Response buffer: 500 tokens reserved for LLM output
- Prompt limit: 1650 tokens (2150 - 500)

Offline Fallback:
The module uses tiktoken for accurate token counting, but falls back to
word-based estimation if tiktoken cannot download its vocabulary data
(e.g., no internet connection, firewall blocking).
"""

from typing import Dict, List


class PromptBuilder:
    """
    Builds LLM prompts with token budget management.

    This class assembles all prompt components (system prompt, profile summary,
    retrieved context, session history, user message) and ensures the total
    token count stays within the budget.

    If components exceed the budget, they are truncated in this priority order:
    1. Retrieved context (most expendable)
    2. Session history (next most expendable)
    3. Profile summary (less expendable)
    4. System prompt (never truncated)
    5. User message (never truncated)

    Attributes:
        encoding: Tiktoken encoding instance (or None if offline fallback)
        use_fallback: Whether to use word-based token estimation
        token_budget: Total token budget (default 2150)
        response_buffer: Tokens reserved for response (default 500)
    """

    def __init__(self, token_budget: int = 2150, response_buffer: int = 500):
        """
        Initialize prompt builder.

        Attempts to load tiktoken encoding for accurate token counting.
        Falls back to word-based estimation if tiktoken fails (offline mode).

        Args:
            token_budget: Total token budget for prompt + response
            response_buffer: Tokens to reserve for LLM response
        """
        self.token_budget = token_budget
        self.response_buffer = response_buffer
        self.prompt_limit = token_budget - response_buffer  # 1650 tokens

        # Try to initialize tiktoken
        self.encoding = None
        self.use_fallback = False

        try:
            import tiktoken
            # Use cl100k_base encoding (GPT-4, GPT-3.5-turbo)
            self.encoding = tiktoken.get_encoding("cl100k_base")
            print("[OK] Tiktoken loaded for accurate token counting")
        except Exception as e:
            # Fallback to word-based estimation
            self.use_fallback = True
            print(f"[OK] Tiktoken unavailable ({type(e).__name__}), using word-based estimation")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Uses tiktoken if available, otherwise falls back to word-based estimation.

        Word-based estimation formula:
        - tokens H words * 1.3 (empirically derived for English text)
        - This tends to overestimate slightly, which is safer for budget management

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        if self.encoding and not self.use_fallback:
            # Use tiktoken for accurate counting
            return len(self.encoding.encode(text))
        else:
            # Fallback: word-based estimation
            # tokens H words * 1.3 (conservative estimate)
            words = len(text.split())
            return int(words * 1.3)

    def build_system_prompt(self, style_summary: str = "") -> str:
        """
        Build the system prompt.

        The system prompt defines the assistant's role and behavior.
        It optionally includes the user's style summary for personalization.

        Args:
            style_summary: User style summary from ProfileManager (optional)

        Returns:
            System prompt string
        """
        base_prompt = """You are a helpful AI assistant. Provide clear, accurate, and helpful responses.
When relevant context from past conversations is provided, use it to give more personalized answers."""

        if style_summary:
            base_prompt += f"\n\nUser communication style: {style_summary}"

        return base_prompt

    def build_full_prompt(
        self,
        user_message: str,
        style_summary: str = "",
        retrieved_context: str = "",
        session_history: str = ""
    ) -> Dict:
        """
        Build complete prompt with all components.

        Assembles all prompt components and ensures total token count is within
        the budget. Components are truncated if necessary to fit the budget.

        Truncation priority (most to least expendable):
        1. Retrieved context
        2. Session history
        3. Style summary (profile)
        4. System prompt (never truncated)
        5. User message (never truncated)

        Args:
            user_message: Current user message
            style_summary: User style summary (optional)
            retrieved_context: Retrieved past exchanges (optional)
            session_history: Recent session messages (optional)

        Returns:
            Dictionary containing:
            - prompt: Complete assembled prompt string
            - retrieved_context: Retrieved context (possibly truncated)
            - token_breakdown: Dict with token counts per component
              - system_prompt: System prompt tokens
              - profile_summary: Style summary tokens
              - retrieved_context: Retrieved context tokens
              - session_history: Session history tokens
              - user_message: User message tokens
              - total: Total prompt tokens
              - budget_remaining: Tokens remaining in budget
              - within_budget: Boolean indicating if within budget
        """
        # Build components
        system_prompt = self.build_system_prompt(style_summary)

        # Count tokens for each component
        tokens_system = self.count_tokens(system_prompt)
        tokens_profile = self.count_tokens(style_summary)
        tokens_message = self.count_tokens(user_message)

        # Start with essential components (never truncated)
        essential_tokens = tokens_system + tokens_message
        remaining_budget = self.prompt_limit - essential_tokens

        # Allocate remaining budget to variable components
        # Priority: session_history > retrieved_context
        tokens_history = 0
        tokens_context = 0
        truncated_history = session_history
        truncated_context = retrieved_context

        # Try to fit profile summary
        if tokens_profile <= remaining_budget:
            remaining_budget -= tokens_profile
        else:
            # Truncate profile summary if needed
            style_summary = self._truncate_to_budget(style_summary, remaining_budget)
            tokens_profile = self.count_tokens(style_summary)
            remaining_budget -= tokens_profile

        # Try to fit session history
        tokens_history = self.count_tokens(session_history)
        if tokens_history <= remaining_budget:
            remaining_budget -= tokens_history
        else:
            # Truncate session history
            truncated_history = self._truncate_to_budget(session_history, remaining_budget)
            tokens_history = self.count_tokens(truncated_history)
            remaining_budget -= tokens_history

        # Try to fit retrieved context with whatever remains
        tokens_context = self.count_tokens(retrieved_context)
        if tokens_context > remaining_budget:
            # Truncate retrieved context
            truncated_context = self._truncate_to_budget(retrieved_context, remaining_budget)
            tokens_context = self.count_tokens(truncated_context)

        # Assemble final prompt
        prompt_parts = [system_prompt]

        if truncated_context:
            prompt_parts.append(f"\nRelevant past conversations:\n{truncated_context}")

        if truncated_history:
            prompt_parts.append(f"\nCurrent session:\n{truncated_history}")

        prompt_parts.append(f"\nUser: {user_message}")

        full_prompt = "\n".join(prompt_parts)

        # Calculate final token counts
        total_tokens = tokens_system + tokens_profile + tokens_context + tokens_history + tokens_message
        budget_remaining = self.prompt_limit - total_tokens
        within_budget = total_tokens <= self.prompt_limit

        return {
            "prompt": full_prompt,
            "retrieved_context": truncated_context,
            "token_breakdown": {
                "system_prompt": tokens_system,
                "profile_summary": tokens_profile,
                "retrieved_context": tokens_context,
                "session_history": tokens_history,
                "user_message": tokens_message,
                "total": total_tokens,
                "budget_remaining": budget_remaining,
                "within_budget": within_budget
            }
        }

    def _truncate_to_budget(self, text: str, budget: int) -> str:
        """
        Truncate text to fit within token budget.

        Uses binary search to find the maximum text length that fits the budget.
        Truncates at word boundaries for clean cuts.

        Args:
            text: Text to truncate
            budget: Token budget to fit within

        Returns:
            Truncated text (empty string if budget too small)
        """
        if budget <= 0:
            return ""

        # Quick check if already within budget
        if self.count_tokens(text) <= budget:
            return text

        # Binary search for maximum length
        words = text.split()
        left, right = 0, len(words)

        best_text = ""
        while left <= right:
            mid = (left + right) // 2
            candidate = " ".join(words[:mid])
            tokens = self.count_tokens(candidate)

            if tokens <= budget:
                best_text = candidate
                left = mid + 1
            else:
                right = mid - 1

        return best_text


# Example usage and testing
if __name__ == "__main__":
    print("=== Prompt Builder Test ===\n")

    # Initialize builder
    builder = PromptBuilder()

    # Test components
    user_message = "I have an error in my code"
    style_summary = "User speaks casually with short messages (avg 8 words). Uses technical terms."
    session_history = "User: Hello\nAssistant: Hi there!"
    retrieved_context = "[Past Exchange 1]\nUser: Previous error\nAssistant: Check your logs"

    # Build prompt
    print("Building prompt...")
    result = builder.build_full_prompt(
        user_message=user_message,
        style_summary=style_summary,
        retrieved_context=retrieved_context,
        session_history=session_history
    )

    # Display results
    print("\n--- Token Breakdown ---")
    breakdown = result['token_breakdown']
    for key, value in breakdown.items():
        print(f"{key:20s}: {value}")

    print("\n--- Full Prompt ---")
    print(result['prompt'])
    print()

    # Test budget enforcement
    print("--- Testing Budget Enforcement ---")
    long_context = "\n".join([f"[Past Exchange {i}]\nUser: Message {i}\nAssistant: Response {i}" for i in range(20)])
    result2 = builder.build_full_prompt(
        user_message="Test message",
        retrieved_context=long_context
    )

    print(f"Long context tokens: {builder.count_tokens(long_context)}")
    print(f"Truncated context tokens: {result2['token_breakdown']['retrieved_context']}")
    print(f"Total tokens: {result2['token_breakdown']['total']}")
    print(f"Within budget: {result2['token_breakdown']['within_budget']}")
    print()

    print("[OK] Test complete")

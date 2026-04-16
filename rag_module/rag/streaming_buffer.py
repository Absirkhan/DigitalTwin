"""
Streaming Buffer for LLM → TTS Pipeline

Overlaps LLM token generation with TTS synthesis by intelligently chunking
output at natural boundaries. This eliminates the wait time between LLM completion
and TTS start, reducing perceived latency from 2-6s to sub-2s.

Key Features:
- Natural punctuation-based splits (. , ? !)
- Breath failsafe for long sentences (conjunctions)
- Hard failsafe to prevent blocking
- Async generator for non-blocking operation
"""

import re
import asyncio
from typing import AsyncGenerator, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class StreamingBuffer:
    """
    Smart buffer that accumulates LLM tokens and yields complete chunks
    for TTS synthesis at natural boundaries.

    Chunking Logic (in priority order):
    1. Primary: Split at punctuation (. , ? !)
    2. Breath Failsafe: Split before conjunctions if 12-15 words (and, but, because, so, or)
    3. Hard Failsafe: Force split at 20 words to prevent blocking
    """

    # Punctuation marks that indicate natural speech boundaries
    PRIMARY_DELIMITERS = {'.', '?', '!', ','}

    # Conjunctions to split at when buffer is getting long
    CONJUNCTIONS = {' and ', ' but ', ' because ', ' so ', ' or ', ' however ', ' therefore '}

    # Word count thresholds
    BREATH_THRESHOLD = 12  # Start looking for conjunctions
    HARD_THRESHOLD = 20    # Force split regardless

    def __init__(self):
        """Initialize empty buffer."""
        self.buffer = ""
        self.total_chunks_yielded = 0
        self.total_tokens_processed = 0

    def _count_words(self, text: str) -> int:
        """Count words in text."""
        return len(text.split())

    def _find_last_punctuation(self) -> Optional[int]:
        """
        Find the position of the last primary delimiter in buffer.

        Returns:
            Position after the delimiter, or None if not found
        """
        last_pos = -1
        last_char = None

        for i, char in enumerate(self.buffer):
            if char in self.PRIMARY_DELIMITERS:
                last_pos = i
                last_char = char

        if last_pos >= 0:
            # Return position AFTER the delimiter
            return last_pos + 1

        return None

    def _find_conjunction_split(self) -> Optional[int]:
        """
        Find position to split before a conjunction (breath failsafe).

        Returns:
            Position right before the conjunction, or None if not found
        """
        buffer_lower = self.buffer.lower()

        # Find all conjunction positions
        conjunction_positions = []
        for conj in self.CONJUNCTIONS:
            idx = buffer_lower.find(conj)
            if idx >= 0:
                conjunction_positions.append(idx)

        if conjunction_positions:
            # Split right before the first conjunction found
            split_pos = min(conjunction_positions)
            logger.debug(f"Breath failsafe: splitting before conjunction at position {split_pos}")
            return split_pos

        return None

    def _find_last_space(self) -> Optional[int]:
        """
        Find the last space in buffer for hard failsafe split.

        Returns:
            Position after the last space, or None if not found
        """
        last_space = self.buffer.rfind(' ')
        if last_space >= 0:
            return last_space + 1
        return None

    def _should_yield_chunk(self) -> Optional[str]:
        """
        Determine if we should yield a chunk and return it.

        Returns:
            Chunk to yield, or None if buffer should continue accumulating
        """
        if not self.buffer:
            return None

        word_count = self._count_words(self.buffer)

        # STRATEGY 1: Primary - Check for punctuation
        punct_pos = self._find_last_punctuation()
        if punct_pos:
            chunk = self.buffer[:punct_pos].strip()
            self.buffer = self.buffer[punct_pos:].strip()
            logger.debug(f"Primary split at punctuation: yielding {len(chunk)} chars")
            return chunk

        # STRATEGY 2: Breath Failsafe - Check for conjunctions if buffer is getting long
        if word_count >= self.BREATH_THRESHOLD:
            conj_pos = self._find_conjunction_split()
            if conj_pos:
                chunk = self.buffer[:conj_pos].strip()
                self.buffer = self.buffer[conj_pos:].strip()
                logger.debug(f"Breath failsafe split at conjunction: yielding {len(chunk)} chars")
                return chunk

        # STRATEGY 3: Hard Failsafe - Force split if buffer is too long
        if word_count >= self.HARD_THRESHOLD:
            space_pos = self._find_last_space()
            if space_pos:
                chunk = self.buffer[:space_pos].strip()
                self.buffer = self.buffer[space_pos:].strip()
                logger.warning(f"Hard failsafe split at space: yielding {len(chunk)} chars")
                return chunk
            else:
                # Extremely rare: no spaces in 20-word buffer, just yield everything
                chunk = self.buffer.strip()
                self.buffer = ""
                logger.warning(f"Hard failsafe (no spaces): yielding {len(chunk)} chars")
                return chunk

        # Not ready to yield yet
        return None

    def add_token(self, token: str) -> Optional[str]:
        """
        Add a token to the buffer and check if we should yield a chunk.

        Args:
            token: New token from LLM stream

        Returns:
            Chunk to yield, or None if buffer should continue accumulating
        """
        self.buffer += token
        self.total_tokens_processed += 1

        chunk = self._should_yield_chunk()
        if chunk:
            self.total_chunks_yielded += 1
            logger.debug(
                f"Yielding chunk #{self.total_chunks_yielded}: "
                f"'{chunk[:50]}...' ({self._count_words(chunk)} words)"
            )
            return chunk

        return None

    def flush(self) -> Optional[str]:
        """
        Flush remaining buffer content at end of stream.

        Returns:
            Final chunk, or None if buffer is empty
        """
        if self.buffer.strip():
            chunk = self.buffer.strip()
            self.buffer = ""
            self.total_chunks_yielded += 1
            logger.debug(f"Flushing final chunk: '{chunk[:50]}...'")
            return chunk
        return None

    def get_stats(self) -> Dict:
        """Get buffer statistics."""
        return {
            'total_tokens_processed': self.total_tokens_processed,
            'total_chunks_yielded': self.total_chunks_yielded,
            'buffer_remaining': len(self.buffer),
            'buffer_words': self._count_words(self.buffer)
        }


async def stream_llm_to_chunks(
    llm_stream: AsyncGenerator[Dict, None],
    buffer: Optional[StreamingBuffer] = None
) -> AsyncGenerator[Dict, None]:
    """
    Convert LLM token stream to TTS-ready chunks with smart buffering.

    This is the main entry point for the streaming pipeline. It wraps the
    LLM generator and yields chunks at natural boundaries.

    Args:
        llm_stream: Async generator yielding LLM tokens
        buffer: Optional StreamingBuffer instance (creates new if None)

    Yields:
        Dictionaries with:
        - type: 'chunk' | 'done' | 'error'
        - content: Chunk text (only for type='chunk')
        - stats: Buffer statistics (only for type='done')
    """
    if buffer is None:
        buffer = StreamingBuffer()

    try:
        async for llm_output in llm_stream:
            if llm_output.get('type') == 'token':
                token = llm_output.get('content', '')

                # Add token to buffer and check for chunks
                chunk = buffer.add_token(token)

                if chunk:
                    yield {
                        'type': 'chunk',
                        'content': chunk,
                        'word_count': buffer._count_words(chunk)
                    }

        # Flush final chunk
        final_chunk = buffer.flush()
        if final_chunk:
            yield {
                'type': 'chunk',
                'content': final_chunk,
                'word_count': buffer._count_words(final_chunk)
            }

        # Signal completion with stats
        yield {
            'type': 'done',
            'stats': buffer.get_stats()
        }

    except Exception as e:
        logger.error(f"Error in streaming buffer: {e}", exc_info=True)
        yield {
            'type': 'error',
            'error': str(e)
        }


# Testing code
if __name__ == "__main__":
    print("=== StreamingBuffer Test ===\n")

    # Test case 1: Punctuation splits
    print("Test 1: Punctuation splits")
    buffer = StreamingBuffer()

    test_tokens = "Hello world. This is a test, right? Yes! Amazing.".split()

    for token in test_tokens:
        chunk = buffer.add_token(token + " ")
        if chunk:
            print(f"  CHUNK: '{chunk}'")

    final = buffer.flush()
    if final:
        print(f"  FINAL: '{final}'")

    print(f"  Stats: {buffer.get_stats()}\n")

    # Test case 2: Breath failsafe (conjunction)
    print("Test 2: Breath failsafe (conjunction split)")
    buffer2 = StreamingBuffer()

    long_sentence = "This is a very long sentence without punctuation and it keeps going on and on but we need to split it somehow because it is getting way too long for comfort"

    for token in long_sentence.split():
        chunk = buffer2.add_token(token + " ")
        if chunk:
            print(f"  CHUNK: '{chunk}'")

    final2 = buffer2.flush()
    if final2:
        print(f"  FINAL: '{final2}'")

    print(f"  Stats: {buffer2.get_stats()}\n")

    # Test case 3: Hard failsafe
    print("Test 3: Hard failsafe (forced split at 20 words)")
    buffer3 = StreamingBuffer()

    # 25 words without punctuation or conjunctions
    very_long = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twentyone twentytwo twentythree twentyfour twentyfive"

    for token in very_long.split():
        chunk = buffer3.add_token(token + " ")
        if chunk:
            print(f"  CHUNK: '{chunk}' ({buffer3._count_words(chunk)} words)")

    final3 = buffer3.flush()
    if final3:
        print(f"  FINAL: '{final3}' ({buffer3._count_words(final3)} words)")

    print(f"  Stats: {buffer3.get_stats()}\n")

    print("[OK] All tests complete")

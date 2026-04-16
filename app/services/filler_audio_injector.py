"""
Filler Audio Injector - Zero-Latency UX Hack with Context-Aware Selection

Instantly plays a filler audio clip when the bot is addressed, BEFORE
the actual RAG/LLM/TTS pipeline begins. This creates the perception of
zero latency by immediately acknowledging the user.

Strategy:
- Bot name detected → Analyze query intent → Select appropriate filler
- INSTANTLY inject context-aware filler MP3 (0-50ms)
- In parallel: Start RAG + LLM + TTS pipeline
- User hears contextually appropriate response immediately
- 1-2 seconds later: Real response plays seamlessly

Context-Aware Filler Selection:
=================================

Category 1: GREETING (Hello, hi, hey, good morning, etc.)
- Triggers: "hello", "hi", "hey", "good morning", "good afternoon", "greetings"
- Fillers:
  * filler_greeting_hello.mp3 (~600ms) - "Hello there!"
  * filler_greeting_hi.mp3 (~900ms) - "Hi! Give me just a moment."
  * filler_greeting_hey.mp3 (~1s) - "Hey! What can I help with?"

Category 2: GOODBYE (Goodbye, bye, see you later, farewell, etc.)
- Triggers: "goodbye", "bye", "see you", "farewell", "take care", "later"
- Fillers:
  * filler_goodbye_bye.mp3 (~1s) - "Goodbye! Have a great day."
  * filler_goodbye_seeyou.mp3 (~1.1s) - "See you later! Take care."
  * filler_goodbye_thanks.mp3 (~1s) - "Thanks for having me. Bye!"

Category 3: ANALYTICAL / RETRIEVAL (Factual questions)
- Triggers: "what is", "how many", "summarize", "data", "numbers", "report", "status"
- Fillers:
  * filler_analytical_check.mp3 (~1s) - "Let me check on that..."
  * filler_analytical_pulling.mp3 (~1s) - "Pulling that up now..."
  * filler_analytical_second.mp3 (~800ms) - "Just a second..."
  * filler_analytical_looking.mp3 (~1s) - "Let me look that up..."

Category 4: OPINION / ABSTRACT (Thoughts, advice, ideas)
- Triggers: "what do you think", "thoughts", "why", "agree", "opinion", "should we"
- Fillers:
  * filler_opinion_hmm.mp3 (~800ms) - "Hmm, let's see..."
  * filler_opinion_good.mp3 (~1.2s) - "That's a good question..."
  * filler_opinion_think.mp3 (~1s) - "Well, I think..."
  * filler_opinion_consider.mp3 (~1s) - "Let me consider that..."

Category 5: ACTION / AFFIRMATION (Commands, requests)
- Triggers: "can you", "please do", "write", "send", "create", "make", "help"
- Fillers:
  * filler_action_sure.mp3 (~600ms) - "Sure thing."
  * filler_action_onit.mp3 (~500ms) - "On it."
  * filler_action_moment.mp3 (~800ms) - "Yep, give me one moment."
  * filler_action_absolutely.mp3 (~700ms) - "Absolutely."

Query Length Heuristic:
=======================
- SHORT query (< 10 words): Use SHORT filler (500-800ms)
  * Fast response expected, don't delay unnecessarily
  * Examples: "Checking.", "Sure.", "On it."

- MEDIUM query (10-25 words): Use MEDIUM filler (800-1200ms)
  * Normal processing time, standard acknowledgment
  * Examples: "Let me check...", "That's a good question..."

- LONG query (> 25 words): Use LONG filler (1500-2500ms)
  * Complex query needs more processing time
  * Buys CPU time while maintaining engagement
  * Examples: "Hmm, that's a really good question, let me think about that..."
"""

import os
import asyncio
import logging
import random
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class FillerAudioInjector:
    """
    Service for injecting instant filler audio when bot is addressed.

    This is the "zero-latency UX hack" that makes the bot feel instant.
    """

    _instance: Optional['FillerAudioInjector'] = None

    # Filler audio directory
    FILLER_DIR = Path("data/filler_audio")

    # Context-aware filler clips organized by category
    FILLER_CLIPS = {
        # ANALYTICAL / RETRIEVAL (Factual questions)
        'analytical_check': {
            'file': 'filler_analytical_check.mp3',
            'text': 'Let me check on that...',
            'duration_ms': 1000,
            'category': 'analytical'
        },
        'analytical_pulling': {
            'file': 'filler_analytical_pulling.mp3',
            'text': 'Pulling that up now...',
            'duration_ms': 1000,
            'category': 'analytical'
        },
        'analytical_second': {
            'file': 'filler_analytical_second.mp3',
            'text': 'Just a second...',
            'duration_ms': 800,
            'category': 'analytical'
        },
        'analytical_looking': {
            'file': 'filler_analytical_looking.mp3',
            'text': 'Let me look that up...',
            'duration_ms': 1000,
            'category': 'analytical'
        },

        # OPINION / ABSTRACT (Thoughts, advice, ideas)
        'opinion_hmm': {
            'file': 'filler_opinion_hmm.mp3',
            'text': 'Hmm, let\'s see...',
            'duration_ms': 800,
            'category': 'opinion'
        },
        'opinion_good': {
            'file': 'filler_opinion_good.mp3',
            'text': 'That\'s a good question...',
            'duration_ms': 1200,
            'category': 'opinion'
        },
        'opinion_think': {
            'file': 'filler_opinion_think.mp3',
            'text': 'Well, I think...',
            'duration_ms': 1000,
            'category': 'opinion'
        },
        'opinion_consider': {
            'file': 'filler_opinion_consider.mp3',
            'text': 'Let me consider that...',
            'duration_ms': 1000,
            'category': 'opinion'
        },

        # ACTION / AFFIRMATION (Commands, requests)
        'action_sure': {
            'file': 'filler_action_sure.mp3',
            'text': 'Sure thing.',
            'duration_ms': 600,
            'category': 'action'
        },
        'action_onit': {
            'file': 'filler_action_onit.mp3',
            'text': 'On it.',
            'duration_ms': 500,
            'category': 'action'
        },
        'action_moment': {
            'file': 'filler_action_moment.mp3',
            'text': 'Yep, give me one moment.',
            'duration_ms': 800,
            'category': 'action'
        },
        'action_absolutely': {
            'file': 'filler_action_absolutely.mp3',
            'text': 'Absolutely.',
            'duration_ms': 700,
            'category': 'action'
        },

        # LONG fillers for complex queries (> 25 words)
        'long_complex': {
            'file': 'filler_long_complex.mp3',
            'text': 'Hmm, that\'s a really good question, let me think about that...',
            'duration_ms': 2500,
            'category': 'long'
        },
        'long_processing': {
            'file': 'filler_long_processing.mp3',
            'text': 'Interesting question. Give me a moment to gather that information...',
            'duration_ms': 2300,
            'category': 'long'
        },

        # GREETING fillers (for hello, hi, hey, etc.)
        'greeting_hello': {
            'file': 'filler_greeting_hello.mp3',
            'text': 'Hello there!',
            'duration_ms': 600,
            'category': 'greeting'
        },
        'greeting_hi': {
            'file': 'filler_greeting_hi.mp3',
            'text': 'Hi! Give me just a moment.',
            'duration_ms': 900,
            'category': 'greeting'
        },
        'greeting_hey': {
            'file': 'filler_greeting_hey.mp3',
            'text': 'Hey! What can I help with?',
            'duration_ms': 1000,
            'category': 'greeting'
        },

        # GOODBYE fillers (for goodbye, bye, see you later, etc.)
        'goodbye_bye': {
            'file': 'filler_goodbye_bye.mp3',
            'text': 'Goodbye! Have a great day.',
            'duration_ms': 1000,
            'category': 'goodbye'
        },
        'goodbye_seeyou': {
            'file': 'filler_goodbye_seeyou.mp3',
            'text': 'See you later! Take care.',
            'duration_ms': 1100,
            'category': 'goodbye'
        },
        'goodbye_thanks': {
            'file': 'filler_goodbye_thanks.mp3',
            'text': 'Thanks for having me. Bye!',
            'duration_ms': 1000,
            'category': 'goodbye'
        },
    }

    # Keyword triggers for each category
    ANALYTICAL_KEYWORDS = [
        'what is', 'how many', 'summarize', 'data', 'numbers', 'report',
        'status', 'show me', 'tell me about', 'explain', 'define',
        'when was', 'where is', 'who is', 'list', 'count'
    ]

    OPINION_KEYWORDS = [
        'what do you think', 'thoughts', 'why', 'agree', 'opinion',
        'should we', 'would you', 'recommend', 'suggest', 'advise',
        'better', 'prefer', 'believe'
    ]

    ACTION_KEYWORDS = [
        'can you', 'please do', 'write', 'send', 'create', 'make',
        'help', 'show', 'generate', 'build', 'update', 'change',
        'add', 'remove', 'delete', 'fix'
    ]

    # Greeting keywords (use dedicated greeting fillers)
    GREETING_KEYWORDS = [
        'hello', 'hi', 'hey', 'good morning', 'good afternoon',
        'good evening', 'greetings', 'howdy', 'yo', 'sup', 'heya'
    ]

    # Goodbye keywords (use dedicated goodbye fillers)
    GOODBYE_KEYWORDS = [
        'goodbye', 'bye', 'see you', 'farewell', 'take care',
        'talk to you later', 'catch you later', 'gotta go',
        'see ya', 'later', 'peace out', 'signing off'
    ]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize filler audio injector."""
        if not hasattr(self, '_initialized_instance'):
            self.FILLER_DIR.mkdir(parents=True, exist_ok=True)
            self._filler_cache = {}  # Cache loaded audio in memory
            self._initialized_instance = True
            logger.info("Filler audio injector initialized")

    def analyze_query_context(self, query_text: str) -> Dict:
        """
        Analyze query to determine intent category and length.

        Args:
            query_text: User's query text (after bot name removal)

        Returns:
            Dictionary with:
            - category: 'greeting' | 'goodbye' | 'analytical' | 'opinion' | 'action' | 'long'
            - word_count: int
            - query_length: 'short' | 'medium' | 'long'
            - confidence: float (0-1)
        """
        query_lower = query_text.lower().strip()
        word_count = len(query_text.split())

        # Determine query length category
        if word_count < 10:
            query_length = 'short'
        elif word_count <= 25:
            query_length = 'medium'
        else:
            query_length = 'long'

        # Check for greetings and goodbyes first (highest priority)
        # Use word boundary matching to avoid false positives (e.g., "the" in "tell me about the TTS")
        import re
        is_greeting = any(re.search(r'\b' + re.escape(kw) + r'\b', query_lower) for kw in self.GREETING_KEYWORDS)
        is_goodbye = any(re.search(r'\b' + re.escape(kw) + r'\b', query_lower) for kw in self.GOODBYE_KEYWORDS)

        # Initialize score variables (needed for return statement)
        analytical_score = 0
        opinion_score = 0
        action_score = 0

        if is_goodbye:
            # Goodbyes get dedicated farewell fillers
            category = 'goodbye'
            confidence = 0.95
        elif is_greeting:
            # Greetings get dedicated greeting fillers
            category = 'greeting'
            confidence = 0.95
        else:
            # Check for category keywords
            analytical_score = sum(1 for kw in self.ANALYTICAL_KEYWORDS if kw in query_lower)
            opinion_score = sum(1 for kw in self.OPINION_KEYWORDS if kw in query_lower)
            action_score = sum(1 for kw in self.ACTION_KEYWORDS if kw in query_lower)

            # Determine category
            max_score = max(analytical_score, opinion_score, action_score)

            if max_score == 0:
                # No keywords matched - default to action for simplicity
                category = 'action'
                confidence = 0.3
            elif analytical_score == max_score:
                category = 'analytical'
                confidence = min(0.9, 0.6 + (analytical_score * 0.1))
            elif action_score == max_score:
                category = 'action'
                confidence = min(0.9, 0.6 + (action_score * 0.1))
            else:
                category = 'opinion'
                confidence = min(0.9, 0.6 + (opinion_score * 0.1))

        # Override with 'long' category for very long queries
        if query_length == 'long':
            category = 'long'
            confidence = 0.9

        logger.debug(
            f"Query analysis: category={category}, length={query_length}, "
            f"words={word_count}, confidence={confidence:.2f}"
        )

        return {
            'category': category,
            'word_count': word_count,
            'query_length': query_length,
            'confidence': confidence,
            'scores': {
                'analytical': analytical_score,
                'opinion': opinion_score,
                'action': action_score
            }
        }

    def select_contextual_filler(
        self,
        query_text: str,
        prefer_short: bool = False
    ) -> Optional[str]:
        """
        Select appropriate filler based on query context and length.

        Args:
            query_text: User's query text
            prefer_short: Force short filler selection (< 800ms)

        Returns:
            Filler name to use, or None if none available
        """
        # Analyze query
        analysis = self.analyze_query_context(query_text)

        category = analysis['category']
        query_length = analysis['query_length']

        # Get candidates from the category
        candidates = [
            name for name, info in self.FILLER_CLIPS.items()
            if info['category'] == category
        ]

        if not candidates:
            # Fallback to opinion category
            candidates = [
                name for name, info in self.FILLER_CLIPS.items()
                if info['category'] == 'opinion'
            ]

        if not candidates:
            logger.warning("No filler candidates found")
            return None

        # Filter by duration if prefer_short or query is short
        if prefer_short or query_length == 'short':
            # Prefer fillers < 800ms for quick responses
            short_candidates = [
                name for name in candidates
                if self.FILLER_CLIPS[name]['duration_ms'] < 800
            ]
            if short_candidates:
                candidates = short_candidates

        # Filter to only available fillers (exist on disk or cached)
        available_candidates = []
        for name in candidates:
            filler_info = self.FILLER_CLIPS[name]
            file_path = self.FILLER_DIR / filler_info['file']

            if name in self._filler_cache or file_path.exists():
                available_candidates.append(name)

        if not available_candidates:
            logger.warning(
                f"No available fillers for category '{category}'. "
                f"Generate filler audio library first."
            )
            return None

        # Randomly select from available candidates
        selected = random.choice(available_candidates)

        logger.debug(
            f"Selected filler: {selected} (category={category}, "
            f"duration={self.FILLER_CLIPS[selected]['duration_ms']}ms)"
        )

        return selected

    def _load_filler_audio(self, filler_name: str) -> Optional[bytes]:
        """
        Load filler audio from disk (with caching).

        Args:
            filler_name: Name of filler clip (e.g., 'analytical_check', 'action_onit')

        Returns:
            Audio bytes, or None if file not found
        """
        # Check cache first
        if filler_name in self._filler_cache:
            return self._filler_cache[filler_name]

        # Load from disk
        filler_info = self.FILLER_CLIPS.get(filler_name)
        if not filler_info:
            logger.warning(f"Unknown filler name: {filler_name}")
            return None

        filename = filler_info['file']
        file_path = self.FILLER_DIR / filename

        if not file_path.exists():
            logger.warning(
                f"Filler audio not found: {file_path}\n"
                f"Please generate or download filler audio files to: {self.FILLER_DIR}"
            )
            return None

        try:
            with open(file_path, 'rb') as f:
                audio_data = f.read()

            # Cache in memory for instant access next time
            self._filler_cache[filler_name] = audio_data

            logger.debug(f"Loaded filler audio: {filename} ({len(audio_data)} bytes)")

            return audio_data

        except Exception as e:
            logger.error(f"Error loading filler audio {filename}: {e}")
            return None

    async def inject_instant_filler(
        self,
        bot_id: str,
        recall_service,
        query_text: str,
        filler_type: str = 'auto'
    ) -> Dict:
        """
        Inject context-aware filler audio INSTANTLY when bot is addressed.

        This must be called IMMEDIATELY upon bot name detection,
        BEFORE starting the RAG/LLM pipeline.

        Args:
            bot_id: ID of the bot to inject audio to
            recall_service: Recall.ai service instance
            query_text: User's query text (for context analysis)
            filler_type: Type of filler ('auto' for context-aware, or specific name)

        Returns:
            Dictionary with:
            - success: bool
            - filler_used: str (name of filler clip)
            - category: str (analytical/opinion/action/long)
            - query_analysis: dict (context analysis results)
            - latency_ms: float
            - message: str
        """
        import time
        start_time = time.time()

        query_analysis = None

        try:
            # Auto-select context-aware filler if requested
            if filler_type == 'auto':
                # Use contextual selection based on query
                filler_type = self.select_contextual_filler(query_text)
                query_analysis = self.analyze_query_context(query_text)

                if not filler_type:
                    logger.warning("No context-aware filler available, skipping instant injection")
                    return {
                        'success': False,
                        'filler_used': None,
                        'category': None,
                        'query_analysis': query_analysis,
                        'latency_ms': (time.time() - start_time) * 1000,
                        'message': 'No filler audio available'
                    }

            # Load filler audio (instant if cached)
            audio_data = self._load_filler_audio(filler_type)

            if not audio_data:
                return {
                    'success': False,
                    'filler_used': filler_type,
                    'category': query_analysis.get('category') if query_analysis else None,
                    'query_analysis': query_analysis,
                    'latency_ms': (time.time() - start_time) * 1000,
                    'message': 'Filler audio not found'
                }

            # Get filler metadata
            filler_info = self.FILLER_CLIPS.get(filler_type, {})
            category = filler_info.get('category', 'unknown')
            filler_text = filler_info.get('text', '')

            # Inject to Recall.ai (non-blocking fire-and-forget)
            # This runs in parallel with the main pipeline
            inject_result = await recall_service.inject_output_audio_mp3(bot_id, audio_data)

            latency_ms = (time.time() - start_time) * 1000

            if inject_result.get('success'):
                logger.info(
                    f"✨ CONTEXT-AWARE FILLER INJECTED: '{filler_type}' "
                    f"(category={category}, text=\"{filler_text}\") → bot {bot_id} "
                    f"(latency: {latency_ms:.0f}ms)"
                )

                return {
                    'success': True,
                    'filler_used': filler_type,
                    'category': category,
                    'filler_text': filler_text,
                    'query_analysis': query_analysis,
                    'latency_ms': latency_ms,
                    'message': 'Context-aware filler audio injected successfully'
                }
            else:
                logger.warning(f"Filler injection failed: {inject_result.get('message')}")

                return {
                    'success': False,
                    'filler_used': filler_type,
                    'category': category,
                    'query_analysis': query_analysis,
                    'latency_ms': latency_ms,
                    'message': inject_result.get('message', 'Injection failed')
                }

        except Exception as e:
            logger.error(f"Error injecting filler audio: {e}", exc_info=True)

            return {
                'success': False,
                'filler_used': filler_type,
                'category': None,
                'query_analysis': query_analysis,
                'latency_ms': (time.time() - start_time) * 1000,
                'message': f'Error: {str(e)}'
            }

    def get_available_fillers(self) -> list:
        """
        Get list of available filler clips.

        Returns:
            List of filler names that are available (exist on disk or cached)
        """
        available = []

        for name, filename in self.FILLER_CLIPS.items():
            if name in self._filler_cache or (self.FILLER_DIR / filename).exists():
                available.append(name)

        return available

    def preload_all_fillers(self):
        """
        Preload all filler audio into memory cache for instant access.

        Call this during app startup to ensure zero-latency injection.
        """
        logger.info("Preloading filler audio into memory...")

        loaded_count = 0
        for name in self.FILLER_CLIPS.keys():
            audio = self._load_filler_audio(name)
            if audio:
                loaded_count += 1

        logger.info(f"Preloaded {loaded_count}/{len(self.FILLER_CLIPS)} filler clips")

        return loaded_count


# Singleton instance
filler_audio_injector = FillerAudioInjector()


# Helper function to generate context-aware filler audio library
async def generate_filler_audio_library():
    """
    Generate context-aware filler audio library using Piper TTS.

    This is a one-time setup script to create all filler audio files.
    Run this once to generate all filler clips.
    """
    from app.services.piper_tts_service import piper_tts_service

    print("=== Generating Context-Aware Filler Audio Library ===\n")

    # Create output directory
    FillerAudioInjector.FILLER_DIR.mkdir(parents=True, exist_ok=True)

    total = len(FillerAudioInjector.FILLER_CLIPS)
    success_count = 0

    for name, info in FillerAudioInjector.FILLER_CLIPS.items():
        text = info['text']
        category = info['category']
        duration = info['duration_ms']

        print(f"Generating '{name}' (category={category}, ~{duration}ms)")
        print(f"  Text: \"{text}\"")

        try:
            # Synthesize audio
            audio_data = await piper_tts_service.synthesize_text(text)

            # Save to file
            output_path = FillerAudioInjector.FILLER_DIR / info['file']

            with open(output_path, 'wb') as f:
                f.write(audio_data)

            print(f"  ✅ Saved: {output_path} ({len(audio_data)} bytes)\n")
            success_count += 1

        except Exception as e:
            print(f"  ❌ Failed: {e}\n")

    print("="*60)
    print(f"[OK] Filler audio library generation complete")
    print(f"     Success: {success_count}/{total} files generated")
    print("="*60)


# Testing code
if __name__ == "__main__":
    print("=== Filler Audio Injector Test ===\n")

    async def test_filler_injection():
        injector = FillerAudioInjector()

        # Check available fillers
        available = injector.get_available_fillers()
        print(f"Available filler clips: {available}")

        if not available:
            print("\n⚠️ No filler audio available!")
            print("Run: python -m app.services.filler_audio_injector --generate")
            return

        # Preload all fillers
        loaded = injector.preload_all_fillers()
        print(f"Preloaded {loaded} filler clips into memory\n")

        print("[OK] Test complete")

    asyncio.run(test_filler_injection())

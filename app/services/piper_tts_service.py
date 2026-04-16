"""
Piper TTS Service - Ultra-Fast CPU Text-to-Speech

Replaces NeuTTS with Piper TTS for sub-2-second latency target.
Piper is optimized for speed on CPU and doesn't require voice cloning,
making it perfect for real-time meeting responses.

Key Features:
- Sub-500ms synthesis for typical responses
- No voice cloning overhead (uses pre-trained voices)
- CPU-optimized with ONNX runtime
- Async/await compatible
- Streaming-ready architecture

Performance Targets:
- 10-15 word sentence: 300-500ms
- 30-40 word response: 800-1200ms
- Total pipeline (LLM + TTS): < 2 seconds

Installation:
    pip install piper-tts

    # Download a voice model (e.g., en_US-lessac-medium)
    # Place in: data/piper_voices/
"""

import os
import asyncio
import logging
import io
import wave
from pathlib import Path
from typing import Optional, AsyncGenerator
import numpy as np

logger = logging.getLogger(__name__)


class PiperTTSService:
    """
    Singleton service for Piper TTS synthesis.

    Optimized for minimal latency in voice assistant applications.
    """

    _instance: Optional['PiperTTSService'] = None
    _piper_engine = None
    _initialized = False

    # Piper voice model settings
    VOICE_MODEL_DIR = Path("data/piper_voices")
    DEFAULT_VOICE = "en_US-lessac-medium"  # Fast and clear
    SAMPLE_RATE = 22050  # Piper default

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize service (model loaded lazily on first use)."""
        if not hasattr(self, '_initialized_instance'):
            self.VOICE_MODEL_DIR.mkdir(parents=True, exist_ok=True)
            self._initialized_instance = True
            logger.info("Piper TTS service initialized (model will load on first use)")

    def _load_model(self, voice_name: Optional[str] = None):
        """
        Lazy-load Piper TTS model on first use.

        Args:
            voice_name: Voice model name (defaults to DEFAULT_VOICE)
        """
        if self._piper_engine is None:
            try:
                logger.info("Loading Piper TTS model (first use)...")

                # Import here to avoid startup overhead
                from piper import PiperVoice

                voice_name = voice_name or self.DEFAULT_VOICE
                model_path = self.VOICE_MODEL_DIR / f"{voice_name}.onnx"
                config_path = self.VOICE_MODEL_DIR / f"{voice_name}.onnx.json"

                if not model_path.exists():
                    logger.error(
                        f"Piper voice model not found: {model_path}\n"
                        f"Please download from: https://github.com/rhasspy/piper/releases\n"
                        f"Place .onnx and .onnx.json files in: {self.VOICE_MODEL_DIR}"
                    )
                    raise FileNotFoundError(f"Voice model not found: {model_path}")

                # Load voice
                self._piper_engine = PiperVoice.load(
                    str(model_path),
                    str(config_path),
                    use_cuda=False  # CPU only for compatibility
                )

                logger.info(f"Piper TTS model loaded: {voice_name}")

            except ImportError:
                logger.error(
                    "piper-tts not installed. Install with: pip install piper-tts"
                )
                raise
            except Exception as e:
                logger.error(f"Failed to load Piper TTS model: {e}")
                raise

        return self._piper_engine

    async def synthesize_text(self, text: str) -> bytes:
        """
        Synthesize text to audio (MP3 format for compatibility).

        Args:
            text: Text to synthesize

        Returns:
            Audio data as MP3 bytes

        Raises:
            Exception: If synthesis fails
        """
        try:
            # Ensure model is loaded
            piper = self._load_model()

            # Synthesize audio (blocking operation)
            loop = asyncio.get_event_loop()
            audio_samples = await loop.run_in_executor(
                None,
                self._synthesize_sync,
                piper,
                text
            )

            # Convert to WAV bytes
            wav_bytes = self._samples_to_wav(audio_samples)

            # Convert to MP3 for Recall.ai compatibility
            mp3_bytes = await self._convert_wav_to_mp3(wav_bytes)

            logger.debug(f"Synthesized {len(text)} chars → {len(mp3_bytes)} bytes MP3")

            return mp3_bytes

        except Exception as e:
            logger.error(f"Piper TTS synthesis failed: {e}", exc_info=True)
            raise

    def _synthesize_sync(self, piper, text: str) -> np.ndarray:
        """
        Synchronous synthesis (called in executor).

        Args:
            piper: Piper voice engine
            text: Text to synthesize

        Returns:
            Audio samples as numpy array
        """
        # Use the correct Piper API method
        # The newer piper-tts returns AudioChunk namedtuples

        if hasattr(piper, 'synthesize'):
            audio_chunks = []

            for chunk in piper.synthesize(text):
                try:
                    # AudioChunk is a dataclass with these attributes:
                    # - audio_int16_bytes: bytes (raw PCM audio)
                    # - audio_int16_array: numpy array (already converted)
                    # - audio_float_array: numpy array (float format)
                    # - sample_rate, sample_channels, sample_width

                    # Method 1: Use pre-converted int16 array (fastest)
                    if hasattr(chunk, 'audio_int16_array'):
                        audio_array = chunk.audio_int16_array
                    # Method 2: Use int16 bytes
                    elif hasattr(chunk, 'audio_int16_bytes'):
                        audio_array = np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)
                    # Method 3: Legacy 'audio' attribute
                    elif hasattr(chunk, 'audio'):
                        audio_bytes = chunk.audio
                        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                    # Method 4: Direct bytes
                    elif isinstance(chunk, bytes):
                        audio_array = np.frombuffer(chunk, dtype=np.int16)
                    # Method 5: Tuple format
                    elif isinstance(chunk, tuple) and len(chunk) > 0:
                        if isinstance(chunk[0], bytes):
                            audio_array = np.frombuffer(chunk[0], dtype=np.int16)
                        else:
                            audio_array = np.array(chunk[0], dtype=np.int16)
                    else:
                        raise ValueError(
                            f"Cannot extract audio from chunk type: {type(chunk)}\n"
                            f"Available attributes: {[a for a in dir(chunk) if not a.startswith('_')]}"
                        )

                    audio_chunks.append(audio_array)

                except Exception as e:
                    logger.error(f"Error processing audio chunk: {e}")
                    # Debug info
                    logger.error(f"Chunk type: {type(chunk)}")
                    logger.error(f"Chunk dir: {dir(chunk)}")
                    if hasattr(chunk, '__dict__'):
                        logger.error(f"Chunk dict: {chunk.__dict__}")
                    raise

            if audio_chunks:
                return np.concatenate(audio_chunks)
            else:
                return np.array([], dtype=np.int16)

        else:
            raise RuntimeError("Piper voice object does not have 'synthesize' method")

    def _samples_to_wav(self, samples: np.ndarray) -> bytes:
        """
        Convert audio samples to WAV format bytes.

        Args:
            samples: Audio samples (int16)

        Returns:
            WAV file as bytes
        """
        # Create WAV file in memory
        wav_buffer = io.BytesIO()

        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.SAMPLE_RATE)
            wav_file.writeframes(samples.tobytes())

        return wav_buffer.getvalue()

    async def _convert_wav_to_mp3(self, wav_bytes: bytes) -> bytes:
        """
        Convert WAV to MP3 using pydub.

        Args:
            wav_bytes: WAV audio bytes

        Returns:
            MP3 audio bytes
        """
        try:
            from pydub import AudioSegment

            loop = asyncio.get_event_loop()

            def convert():
                # Load WAV from bytes
                audio = AudioSegment.from_wav(io.BytesIO(wav_bytes))

                # Export to MP3
                mp3_buffer = io.BytesIO()
                audio.export(mp3_buffer, format='mp3', bitrate='128k')

                return mp3_buffer.getvalue()

            return await loop.run_in_executor(None, convert)

        except ImportError:
            logger.warning("pydub not installed, returning WAV instead of MP3")
            # Fallback: return WAV if pydub not available
            return wav_bytes
        except Exception as e:
            logger.error(f"MP3 conversion failed: {e}")
            return wav_bytes

    async def synthesize_chunks(
        self,
        text_chunks: AsyncGenerator[str, None]
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize text chunks as they arrive (streaming mode).

        This method enables overlap between LLM generation and TTS synthesis.
        As soon as a chunk arrives from the LLM buffer, it's synthesized
        without waiting for the full response.

        Args:
            text_chunks: Async generator yielding text chunks

        Yields:
            Audio bytes for each chunk (MP3 format)
        """
        try:
            async for chunk_dict in text_chunks:
                if chunk_dict.get('type') == 'chunk':
                    text = chunk_dict.get('content', '')

                    if text.strip():
                        logger.debug(f"Synthesizing chunk: '{text[:30]}...'")

                        # Synthesize this chunk
                        audio_bytes = await self.synthesize_text(text)

                        yield {
                            'type': 'audio_chunk',
                            'audio_data': audio_bytes,
                            'text': text,
                            'size_bytes': len(audio_bytes)
                        }

                elif chunk_dict.get('type') == 'done':
                    # Signal completion
                    yield {
                        'type': 'done',
                        'stats': chunk_dict.get('stats', {})
                    }

                elif chunk_dict.get('type') == 'error':
                    yield chunk_dict
                    break

        except Exception as e:
            logger.error(f"Error in streaming synthesis: {e}", exc_info=True)
            yield {
                'type': 'error',
                'error': str(e)
            }


# Singleton instance
piper_tts_service = PiperTTSService()


# Testing code
if __name__ == "__main__":
    import time

    print("=== Piper TTS Service Test ===\n")

    async def test_synthesis():
        service = PiperTTSService()

        # Test case 1: Single sentence
        print("Test 1: Single sentence synthesis")
        text = "Hello, this is a test of the Piper TTS system."

        start = time.time()
        audio = await service.synthesize_text(text)
        latency = (time.time() - start) * 1000

        print(f"  Text: '{text}'")
        print(f"  Audio size: {len(audio)} bytes")
        print(f"  Latency: {latency:.0f}ms")
        print()

        # Test case 2: Longer response
        print("Test 2: Longer response (typical assistant answer)")
        text2 = "The database we decided to use is PostgreSQL. It provides excellent performance and reliability. We're using SQLAlchemy as the ORM."

        start2 = time.time()
        audio2 = await service.synthesize_text(text2)
        latency2 = (time.time() - start2) * 1000

        print(f"  Text length: {len(text2)} chars")
        print(f"  Audio size: {len(audio2)} bytes")
        print(f"  Latency: {latency2:.0f}ms")
        print()

        print("[OK] Test complete")

    # Run async test
    asyncio.run(test_synthesis())

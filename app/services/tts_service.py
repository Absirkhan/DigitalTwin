"""
NeuTTS Nano Text-to-Speech Service

Provides voice cloning functionality using NeuTTS Nano:
- One-time voice encoding from reference audio
- Persistent voice profile storage per user
- Fast CPU inference with Q4 GGUF model
- Sentence-level streaming for reduced latency
"""
import os
import re
import asyncio
import logging
from pathlib import Path
from typing import Optional, Tuple, List, AsyncGenerator
import torch
import numpy as np
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class TTSService:
    """
    Singleton service for NeuTTS Nano voice synthesis.

    Model is lazy-loaded on first use to avoid startup overhead.
    All blocking operations use asyncio.run_in_executor for async compatibility.
    """

    _instance: Optional['TTSService'] = None
    _tts_model = None
    _initialized = False

    BASE_VOICE_DIR = Path("data/voice_profiles")
    SAMPLE_RATE = 24000

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize service (model loaded lazily on first use)."""
        if not hasattr(self, '_initialized_instance'):
            self._setup_espeak_windows()
            self.BASE_VOICE_DIR.mkdir(parents=True, exist_ok=True)
            self._initialized_instance = True
            logger.info("TTS service initialized (model will load on first use)")

    def _setup_espeak_windows(self):
        """
        Auto-configure espeak-ng environment variables on Windows.

        NeuTTS requires espeak-ng for phonemization. On Windows, if the env vars
        aren't set, we attempt to set them to the default installation path.
        """
        if os.name == 'nt':  # Windows
            if not os.getenv('PHONEMIZER_ESPEAK_LIBRARY'):
                default_lib = r"C:\Program Files\eSpeak NG\libespeak-ng.dll"
                if os.path.exists(default_lib):
                    os.environ['PHONEMIZER_ESPEAK_LIBRARY'] = default_lib
                    logger.info(f"Set PHONEMIZER_ESPEAK_LIBRARY to {default_lib}")
                else:
                    logger.warning(
                        "espeak-ng not found at default location. "
                        "Please set PHONEMIZER_ESPEAK_LIBRARY environment variable."
                    )

            if not os.getenv('PHONEMIZER_ESPEAK_PATH'):
                default_path = r"C:\Program Files\eSpeak NG"
                if os.path.exists(default_path):
                    os.environ['PHONEMIZER_ESPEAK_PATH'] = default_path
                    logger.info(f"Set PHONEMIZER_ESPEAK_PATH to {default_path}")

    def _load_model(self):
        """
        Lazy-load NeuTTS model on first use.

        Uses Q4 GGUF for fastest CPU inference.
        """
        if self._tts_model is None:
            try:
                logger.info("Loading NeuTTS Nano model (first use, may take ~30s)...")
                from neutts import NeuTTS

                self._tts_model = NeuTTS(
                    backbone_repo="neuphonic/neutts-nano-q4-gguf",
                    backbone_device="cpu",
                    codec_repo="neuphonic/neucodec",
                    codec_device="cpu"
                )
                logger.info("NeuTTS model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load NeuTTS model: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"TTS model initialization failed: {str(e)}"
                )
        return self._tts_model

    def _get_user_voice_dir(self, user_id: str) -> Path:
        """Get voice profile directory for a specific user."""
        return self.BASE_VOICE_DIR / str(user_id)

    def _get_ref_codes_path(self, user_id: str) -> Path:
        """Get path to saved reference codes."""
        return self._get_user_voice_dir(user_id) / "ref_codes.pt"

    def _get_ref_text_path(self, user_id: str) -> Path:
        """Get path to saved reference text."""
        return self._get_user_voice_dir(user_id) / "ref_text.txt"

    def _get_ref_audio_path(self, user_id: str) -> Path:
        """Get path to saved reference audio file."""
        return self._get_user_voice_dir(user_id) / "ref_audio.wav"

    async def encode_and_save_voice(
        self,
        user_id: str,
        audio_file_path: str,
        ref_text: str
    ) -> None:
        """
        Encode reference audio and save voice profile.

        This is called ONCE per user to create their voice profile.
        The encoded reference codes are saved and reused for all future synthesis.

        Args:
            user_id: User identifier
            audio_file_path: Path to reference audio file (.wav or .mp3)
            ref_text: Transcript of what was said in the reference audio

        Raises:
            HTTPException: If encoding fails or audio file is invalid
        """
        try:
            # Ensure model is loaded
            tts = self._load_model()

            # Create user directory
            user_dir = self._get_user_voice_dir(user_id)
            user_dir.mkdir(parents=True, exist_ok=True)

            # Encode reference audio (blocking operation)
            logger.info(f"Encoding voice profile for user {user_id}...")
            loop = asyncio.get_event_loop()
            ref_codes = await loop.run_in_executor(
                None,
                tts.encode_reference,
                audio_file_path
            )

            # Save reference codes
            ref_codes_path = self._get_ref_codes_path(user_id)
            await loop.run_in_executor(
                None,
                torch.save,
                ref_codes,
                str(ref_codes_path)
            )

            # Save reference text
            ref_text_path = self._get_ref_text_path(user_id)
            ref_text_path.write_text(ref_text, encoding='utf-8')

            # Save original reference audio for playback
            import shutil
            ref_audio_path = self._get_ref_audio_path(user_id)
            await loop.run_in_executor(
                None,
                shutil.copy2,
                audio_file_path,
                str(ref_audio_path)
            )

            logger.info(f"Voice profile saved for user {user_id}")

        except Exception as e:
            logger.error(f"Voice encoding failed for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Voice encoding failed: {str(e)}"
            )

    def has_voice_profile(self, user_id: str) -> bool:
        """
        Check if user has a saved voice profile.

        Returns True only if both ref_codes.pt and ref_text.txt exist.
        """
        ref_codes_exists = self._get_ref_codes_path(user_id).exists()
        ref_text_exists = self._get_ref_text_path(user_id).exists()
        return ref_codes_exists and ref_text_exists

    def get_ref_audio_path(self, user_id: str) -> Optional[Path]:
        """
        Get the path to the user's original reference audio file.

        Returns:
            Path to ref_audio.wav if it exists, None otherwise
        """
        ref_audio_path = self._get_ref_audio_path(user_id)
        return ref_audio_path if ref_audio_path.exists() else None

    def get_ref_text(self, user_id: str) -> Optional[str]:
        """
        Get the reference text for the user's voice profile.

        Returns:
            Reference text if it exists, None otherwise
        """
        ref_text_path = self._get_ref_text_path(user_id)
        if ref_text_path.exists():
            return ref_text_path.read_text(encoding='utf-8')
        return None

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences for chunked synthesis.

        Uses regex to split on sentence boundaries while preserving punctuation.

        Args:
            text: Input text to split

        Returns:
            List of sentences
        """
        # Split on sentence-ending punctuation (.!?) followed by space or end of string
        # Preserve the punctuation in the sentence
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())

        # Filter out empty strings
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences if sentences else [text]

    async def synthesize_speech(self, user_id: str, text: str) -> np.ndarray:
        """
        Synthesize speech using saved voice profile.

        Args:
            user_id: User identifier
            text: Text to synthesize

        Returns:
            Audio waveform as numpy array (24000 Hz sample rate)

        Raises:
            HTTPException: If voice profile not found or synthesis fails
        """
        if not self.has_voice_profile(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Voice profile not found. Please upload a voice sample first."
            )

        try:
            # Ensure model is loaded
            tts = self._load_model()

            # Load saved reference codes
            ref_codes_path = self._get_ref_codes_path(user_id)
            ref_text_path = self._get_ref_text_path(user_id)

            loop = asyncio.get_event_loop()

            ref_codes = await loop.run_in_executor(
                None,
                torch.load,
                str(ref_codes_path)
            )

            ref_text = ref_text_path.read_text(encoding='utf-8')

            # Synthesize speech (blocking operation)
            logger.info(f"Synthesizing speech for user {user_id}: '{text[:50]}...'")
            wav = await loop.run_in_executor(
                None,
                tts.infer,
                text,
                ref_codes,
                ref_text
            )

            logger.info(f"Speech synthesis completed for user {user_id}")
            return wav

        except Exception as e:
            logger.error(f"Speech synthesis failed for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Speech synthesis failed: {str(e)}"
            )

    async def synthesize_speech_chunked(
        self,
        user_id: str,
        text: str
    ) -> Tuple[np.ndarray, dict]:
        """
        Synthesize speech with sentence-level chunking for reduced perceived latency.

        This method splits text into sentences and synthesizes them sequentially,
        allowing the first chunk to be returned faster than full synthesis.

        Args:
            user_id: User identifier
            text: Text to synthesize

        Returns:
            Tuple of (complete audio array, metadata dict with chunk_count and timings)

        Raises:
            HTTPException: If voice profile not found or synthesis fails
        """
        if not self.has_voice_profile(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Voice profile not found. Please upload a voice sample first."
            )

        try:
            import time

            start_time = time.time()

            # Split into sentences for chunked synthesis
            sentences = self._split_into_sentences(text)
            num_chunks = len(sentences)

            logger.info(f"Synthesizing {num_chunks} sentence(s) for user {user_id}")

            # Load model and reference data
            tts = self._load_model()
            ref_codes_path = self._get_ref_codes_path(user_id)
            ref_text_path = self._get_ref_text_path(user_id)

            loop = asyncio.get_event_loop()

            ref_codes = await loop.run_in_executor(
                None,
                torch.load,
                str(ref_codes_path)
            )
            ref_text = ref_text_path.read_text(encoding='utf-8')

            # Synthesize each sentence
            audio_chunks = []
            chunk_timings = []

            for i, sentence in enumerate(sentences):
                chunk_start = time.time()

                logger.info(f"Synthesizing chunk {i+1}/{num_chunks}: '{sentence[:30]}...'")

                wav_chunk = await loop.run_in_executor(
                    None,
                    tts.infer,
                    sentence,
                    ref_codes,
                    ref_text
                )

                audio_chunks.append(wav_chunk)
                chunk_time = time.time() - chunk_start
                chunk_timings.append(chunk_time)

                logger.info(f"Chunk {i+1}/{num_chunks} completed in {chunk_time:.2f}s")

            # Concatenate all audio chunks
            if len(audio_chunks) > 1:
                # Add small silence between sentences (0.2 seconds)
                silence = np.zeros(int(self.SAMPLE_RATE * 0.2), dtype=audio_chunks[0].dtype)

                combined_audio = []
                for i, chunk in enumerate(audio_chunks):
                    combined_audio.append(chunk)
                    if i < len(audio_chunks) - 1:  # Don't add silence after last chunk
                        combined_audio.append(silence)

                final_audio = np.concatenate(combined_audio)
            else:
                final_audio = audio_chunks[0]

            total_time = time.time() - start_time

            metadata = {
                'chunk_count': num_chunks,
                'chunk_timings': chunk_timings,
                'total_time': total_time,
                'first_chunk_time': chunk_timings[0] if chunk_timings else 0,
                'avg_chunk_time': sum(chunk_timings) / len(chunk_timings) if chunk_timings else 0
            }

            logger.info(
                f"Speech synthesis completed for user {user_id}: "
                f"{num_chunks} chunks in {total_time:.2f}s "
                f"(first chunk: {metadata['first_chunk_time']:.2f}s)"
            )

            return final_audio, metadata

        except Exception as e:
            logger.error(f"Chunked speech synthesis failed for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Speech synthesis failed: {str(e)}"
            )

    async def delete_voice_profile(self, user_id: str) -> None:
        """
        Delete user's voice profile from disk.

        Removes the entire user directory including ref_codes.pt and ref_text.txt.
        """
        import shutil

        user_dir = self._get_user_voice_dir(user_id)
        if user_dir.exists():
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                shutil.rmtree,
                str(user_dir)
            )
            logger.info(f"Voice profile deleted for user {user_id}")


# Singleton instance
tts_service = TTSService()

"""
Voice processing and cloning service
"""

import os
import librosa
import soundfile as sf
from typing import BinaryIO
from celery import current_task

from app.core.celery import celery_app
from app.core.config import settings


class VoiceProcessor:
    def __init__(self):
        self.sample_rate = 22050
        self.model_path = settings.VOICE_MODEL_PATH
    
    def preprocess_audio(self, audio_file: BinaryIO, output_path: str) -> dict:
        """Preprocess audio file for voice training"""
        # Load audio
        audio, sr = librosa.load(audio_file, sr=self.sample_rate)
        
        # Normalize audio
        audio = librosa.util.normalize(audio)
        
        # Remove silence
        audio, _ = librosa.effects.trim(audio, top_db=20)
        
        # Save processed audio
        sf.write(output_path, audio, self.sample_rate)
        
        return {
            "duration": len(audio) / self.sample_rate,
            "sample_rate": self.sample_rate,
            "file_path": output_path
        }
    
    def extract_features(self, audio_path: str) -> dict:
        """Extract voice features for training"""
        audio, sr = librosa.load(audio_path, sr=self.sample_rate)
        
        # Extract MFCC features
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        
        # Extract pitch features
        pitches, magnitudes = librosa.piptrack(y=audio, sr=sr)
        
        # Extract spectral features
        spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)
        spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)
        
        return {
            "mfccs": mfccs.tolist(),
            "pitch": pitches.tolist(),
            "spectral_centroids": spectral_centroids.tolist(),
            "spectral_rolloff": spectral_rolloff.tolist()
        }


@celery_app.task(bind=True)
def process_voice_sample(self, audio_path: str, twin_id: int):
    """Background task to process voice sample"""
    try:
        processor = VoiceProcessor()
        
        # Update task progress
        self.update_state(state='PROGRESS', meta={'progress': 25})
        
        # Extract features
        features = processor.extract_features(audio_path)
        
        self.update_state(state='PROGRESS', meta={'progress': 75})
        
        # Here you would train/update the voice model
        # This is a placeholder for actual voice cloning implementation
        
        self.update_state(state='PROGRESS', meta={'progress': 100})
        
        return {
            'status': 'completed',
            'features': features,
            'twin_id': twin_id
        }
    
    except Exception as exc:
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc)}
        )
        raise


@celery_app.task(bind=True)
def generate_speech(self, text: str, twin_id: int, output_path: str):
    """Background task to generate speech using voice model"""
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'progress': 25})
        
        # Load voice model for the twin
        model_path = os.path.join(settings.VOICE_MODEL_PATH, f"twin_{twin_id}")
        
        self.update_state(state='PROGRESS', meta={'progress': 50})
        
        # Generate speech (placeholder implementation)
        # In a real implementation, you would use a TTS model like Tacotron2, FastSpeech2, etc.
        
        self.update_state(state='PROGRESS', meta={'progress': 100})
        
        return {
            'status': 'completed',
            'audio_path': output_path,
            'text': text
        }
    
    except Exception as exc:
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc)}
        )
        raise
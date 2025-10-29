"""
Summarization service using fine-tuned FLAN-T5 model with LoRA adapters
Integrated with proven working inference model
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import warnings

# Try to import PyTorch dependencies with fallback
try:
    import torch
    from transformers import AutoTokenizer, T5ForConditionalGeneration
    from peft import PeftModel
    TORCH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: PyTorch dependencies not available: {e}")
    torch = None
    AutoTokenizer = None
    T5ForConditionalGeneration = None
    PeftModel = None
    TORCH_AVAILABLE = False

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


class SummarizationService:
    """
    Service for generating summaries using a fine-tuned FLAN-T5 model with LoRA adapters
    Uses the proven working inference model with chunking support
    """
    
    def __init__(self, model_path: Optional[str] = None, base_model: str = "google/flan-t5-large"):
        """
        Initialize the summarization service
        
        Args:
            model_path: Path to the LoRA adapter weights directory
            base_model: Base model name (default: google/flan-t5-large)
        """
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available - summarization service will be disabled")
            self.model = None
            self.tokenizer = None
            self.device = None
            return
            
        self.base_model = base_model
        self.model_path = model_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "app", "ml_models", "weights"
        )
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Model generation parameters (matching working inference script)
        self.max_source_length = 512
        self.max_target_length = 300  # Increased for detailed summaries
        
        logger.info(f"🖥️  Using device: {self.device}")
        logger.info(f"📊 Base model: {self.base_model}")
        
        self._load_model()
    
    def _load_model(self):
        """Load the fine-tuned model and tokenizer (matching working inference script)"""
        try:
            logger.info(f"📚 Loading model from {self.model_path}")
            
            # Check if adapter files exist
            adapter_config_path = os.path.join(self.model_path, "adapter_config.json")
            if not os.path.exists(adapter_config_path):
                raise FileNotFoundError(f"❌ Adapter config not found at {adapter_config_path}")
            
            # Load tokenizer from base model directly to avoid version issues
            logger.info(f"📚 Loading tokenizer from base model: {self.base_model}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.base_model)
            
            # Ensure pad token is set
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load base model
            logger.info(f"🤖 Loading base model: {self.base_model}")
            self.model = T5ForConditionalGeneration.from_pretrained(
                self.base_model,
                torch_dtype=torch.float32,  # Use float32 for stability in inference
                device_map="auto" if self.device == "cuda" else None
            )
            
            # Load LoRA adapter
            logger.info(f"🔧 Loading LoRA adapter from: {self.model_path}")
            self.model = PeftModel.from_pretrained(self.model, self.model_path)
            logger.info("✅ LoRA adapter loaded successfully")
            
            # Move model to device and set to eval mode
            if self.device == "cpu":
                self.model = self.model.to(self.device)
            self.model.eval()
            
            logger.info(f"✅ Model ready for inference")
            
        except Exception as e:
            logger.error(f"❌ Error loading model: {e}")
            raise RuntimeError(f"Failed to load summarization model: {e}")

    
    def format_input(self, dialogue: str) -> str:
        """
        Format input matching the working inference script
        
        Args:
            dialogue: Meeting transcript text
            
        Returns:
            Formatted prompt for the model
        """
        return (
            f"Summarize the following dialogue in third-person narrative form, "
            f"removing all speaker tags, and focusing on the emotions and actions expressed "
            f"and focusing only on important events and personal updates. Avoid repetition. "
            f"meeting participants are absir ahmed khan and rihab rabbani:\n\n {dialogue}"
        )
    
    def chunk_text(self, text: str, max_words: int = 300) -> list:
        """
        Split text into meaningful chunks preserving dialogue structure
        (Direct implementation from working inference script)
        
        Args:
            text: Input text to chunk
            max_words: Maximum words per chunk
            
        Returns:
            List of text chunks
        """
        words = text.split()
        total_words = len(words)
        
        if total_words <= max_words:
            return [text]
        
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_word_count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            line_words = len(line.split())
            
            # If adding this line would exceed limit, finalize current chunk
            if current_word_count + line_words > max_words and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_word_count = line_words
            else:
                current_chunk.append(line)
                current_word_count += line_words
        
        # Add the last chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        # If no good chunks, fall back to word-based chunking
        if not chunks or len(chunks) == 1 and total_words > max_words:
            chunks = []
            for i in range(0, total_words, max_words):
                chunk = ' '.join(words[i:i + max_words])
                chunks.append(chunk)
        
        return chunks

    
    def generate_summary(self, dialogue: str, max_length: Optional[int] = None) -> str:
        """
        Generate summary with settings matching the working inference script
        
        Args:
            dialogue: Input dialogue/transcript text
            max_length: Maximum length of summary (uses default if None)
            
        Returns:
            Generated summary
        """
        if not TORCH_AVAILABLE:
            return "Summary service unavailable - PyTorch not properly installed"
            
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not loaded. Please initialize the service first.")
        
        if max_length is None:
            max_length = self.max_target_length
            
        try:
            input_text = self.format_input(dialogue)
            
            # Tokenize
            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                max_length=self.max_source_length,
                truncation=True,
                padding=True
            )
            
            # Move to device
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            # Calculate dynamic min length
            input_words = len(dialogue.split())
            min_length = max(80, min(int(max_length * 0.4), int(input_words * 0.3)))
            
            # Generate with settings from working inference script
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=200,
                    num_beams=4,
                    min_length=44,
                    repetition_penalty=2.5,
                    no_repeat_ngram_size=4,
                    length_penalty=0.9,
                    early_stopping=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            
            # Decode
            summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Remove duplicate sentences
            sentences = summary.split('. ')
            unique_summary = '. '.join(dict.fromkeys(sentences))
            
            return unique_summary.strip()
            
        except Exception as e:
            logger.error(f"❌ Error generating summary: {e}")
            raise RuntimeError(f"Failed to generate summary: {e}")
    
    def generate_chunked_summary(self, text: str, max_chunk_words: int = 300) -> str:
        """
        Generate summary for large text by processing in chunks
        (Direct implementation from working inference script)
        
        Args:
            text: Input text to summarize
            max_chunk_words: Maximum words per chunk
            
        Returns:
            Combined summary from all chunks
        """
        total_words = len(text.split())
        logger.info(f"📊 Input: {total_words} words")
        
        if total_words <= max_chunk_words:
            logger.info("📝 Processing as single chunk")
            return self.generate_summary(text)
        
        # Split into chunks
        chunks = self.chunk_text(text, max_chunk_words)
        logger.info(f"🔪 Split into {len(chunks)} chunks")
        
        summaries = []
        for i, chunk in enumerate(chunks, 1):
            chunk_words = len(chunk.split())
            logger.info(f"📋 Processing chunk {i}/{len(chunks)} ({chunk_words} words)...")
            
            try:
                chunk_summary = self.generate_summary(chunk)
                if chunk_summary and len(chunk_summary.split()) >= 5:
                    summaries.append(chunk_summary)
                    logger.info(f"✅ Chunk {i} summary: {len(chunk_summary.split())} words")
                else:
                    logger.warning(f"⚠️ Chunk {i} produced short summary, skipping")
            except Exception as e:
                logger.error(f"❌ Error processing chunk {i}: {e}")
        
        if not summaries:
            return "Error: Could not generate summary from any chunk"
        
        # Combine summaries
        if len(summaries) == 1:
            combined = summaries[0]
        else:
            # Join summaries with proper formatting
            combined = ". ".join(s.strip('.') for s in summaries) + "."
        
        # Clean up
        combined = combined.replace('..', '.').replace('  ', ' ').strip()
        
        combined_words = len(combined.split())
        compression_ratio = combined_words / total_words
        logger.info(f"📏 Final summary: {combined_words} words ({compression_ratio:.1%} compression)")
        
        return combined

    
    def generate_meeting_summary(self, transcript: str) -> Dict[str, Any]:
        """
        Generate a comprehensive meeting summary with chunking support
        
        Args:
            transcript: Meeting transcript text
            
        Returns:
            Dictionary containing summary and status
        """
        try:
            # Use chunked processing for better results
            main_summary = self.generate_chunked_summary(transcript, max_chunk_words=300)
            
            return {
                "summary": main_summary,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating meeting summary: {e}")
            return {
                "summary": None,
                "status": "error",
                "error": str(e)
            }
    
    def generate_simple_meeting_summary(self, transcript: str) -> str:
        """
        Generate a simple meeting summary using chunked processing
        Main entry point for the API endpoint
        
        Args:
            transcript: Meeting transcript text
            
        Returns:
            Summary string
        """
        try:
            logger.info(f"📝 Starting summary generation for {len(transcript.split())} words")
            
            # Use the proven chunked processing approach
            summary = self.generate_chunked_summary(transcript, max_chunk_words=300)
            
            logger.info(f"✅ Summary generated successfully")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generating simple meeting summary: {e}")
            return f"Error generating summary: {str(e)}"
    
    def generate_quick_summary(self, text: str, max_words: int = 100) -> str:
        """
        Generate a quick, concise summary
        
        Args:
            text: Input text
            max_words: Maximum number of words in summary
            
        Returns:
            Concise summary
        """
        # For quick summaries, use single-chunk processing
        return self.generate_summary(text)


# Singleton instance
_summarization_service = None


def get_summarization_service() -> SummarizationService:
    """Get the singleton summarization service instance"""
    global _summarization_service
    if _summarization_service is None:
        _summarization_service = SummarizationService()
    return _summarization_service


def generate_summary(text: str, **kwargs) -> str:
    """Convenience function to generate a summary"""
    service = get_summarization_service()
    return service.generate_summary(text, **kwargs)


def generate_meeting_summary(transcript: str) -> Dict[str, Any]:
    """Convenience function to generate a meeting summary"""
    if not TORCH_AVAILABLE:
        return {
            "status": "error",
            "summary": "Summary service unavailable - PyTorch not properly installed",
            "action_items": [],
            "key_decisions": [],
            "error": "PyTorch dependencies not available"
        }
    
    service = get_summarization_service()
    return service.generate_meeting_summary(transcript)


def generate_simple_meeting_summary(transcript: str) -> str:
    """Convenience function to generate a simple meeting summary (just text)"""
    if not TORCH_AVAILABLE:
        return "Summary service unavailable - PyTorch not properly installed"
    
    service = get_summarization_service()
    return service.generate_simple_meeting_summary(transcript)

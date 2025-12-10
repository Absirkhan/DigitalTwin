"""
Summarization service using fine-tuned FLAN-T5-base model
Optimized for meeting transcript summarization with structured output parsing
"""

import os
import re
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import warnings

# Try to import PyTorch dependencies with fallback
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    TORCH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: PyTorch dependencies not available: {e}")
    torch = None
    AutoTokenizer = None
    AutoModelForSeq2SeqLM = None
    TORCH_AVAILABLE = False

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


class SummarizationService:
    """
    Service for generating structured meeting summaries using fine-tuned FLAN-T5-base model

    Model Specifications:
    - Base: google/flan-t5-base (248M parameters)
    - Fine-tuned on 900 meeting dialogue-summary pairs
    - ROUGE-1: 52.16%, ROUGE-2: 39.06%, ROUGE-L: 47.76%
    - Max input: 512 tokens (~1,500 characters)
    - Output format: Structured (Attendees, Key Points, Decisions, Action Items)
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the summarization service

        Args:
            model_path: Path to fine-tuned model directory (default: best_model/)
        """
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available - summarization service will be disabled")
            self.model = None
            self.tokenizer = None
            self.device = None
            return

        # Set model path - default to best_model/ in project root
        if model_path is None:
            project_root = Path(__file__).parent.parent.parent
            model_path = str(project_root / "best_model")

        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Model parameters optimized for your fine-tuned model
        self.max_input_length = 512  # Token limit from your training
        self.max_output_length = 256  # For structured summaries
        self.chunk_size = 1200  # Characters per chunk (~300 tokens)
        self.chunk_overlap = 200  # Overlap for context preservation

        logger.info(f"🖥️  Device: {self.device} ({'GPU' if torch.cuda.is_available() else 'CPU'})")
        logger.info(f"📁 Model path: {self.model_path}")

        self._load_model()

    def _load_model(self):
        """Load the fine-tuned FLAN-T5 model and tokenizer"""
        try:
            logger.info(f"📚 Loading fine-tuned FLAN-T5 model from {self.model_path}")

            # Verify model files exist
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"❌ Model directory not found: {self.model_path}")

            config_path = os.path.join(self.model_path, "config.json")
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"❌ Model config not found at {config_path}")

            # Load tokenizer from fine-tuned model
            logger.info("📚 Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)

            # Ensure pad token is set
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Load fine-tuned model directly (no PEFT/LoRA)
            logger.info("🤖 Loading fine-tuned model...")
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float32,  # Use float32 for stability
                device_map="auto" if self.device.type == "cuda" else None
            )

            # Move to device and set to eval mode
            if self.device.type == "cpu":
                self.model = self.model.to(self.device)
            self.model.eval()

            logger.info("✅ Model loaded successfully and ready for inference")

            # Log model statistics
            param_count = sum(p.numel() for p in self.model.parameters())
            logger.info(f"📊 Model parameters: {param_count:,} (~{param_count/1e6:.0f}M)")

        except Exception as e:
            logger.error(f"❌ Error loading model: {e}")
            raise RuntimeError(f"Failed to load summarization model: {e}")

    def format_input(self, dialogue: str) -> str:
        """
        Format input according to your model's training format

        Args:
            dialogue: Meeting transcript text

        Returns:
            Formatted prompt: "Summarize: [dialogue text]"
        """
        return f"Summarize: {dialogue}"

    def chunk_text(self, text: str, max_chars: int = 1200, overlap: int = 200) -> List[str]:
        """
        Split long transcripts into overlapping chunks for processing

        Strategy:
        1. Try to break at sentence boundaries (. ! ?)
        2. If no good break point, split at word boundaries
        3. Add overlap between chunks for context preservation

        Args:
            text: Input text to chunk
            max_chars: Maximum characters per chunk (default: 1200 = ~300 tokens)
            overlap: Overlap between chunks (default: 200 chars)

        Returns:
            List of text chunks
        """
        if len(text) <= max_chars:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            # Calculate end position
            end = min(start + max_chars, len(text))

            # Try to find a sentence boundary within the last 20% of the chunk
            if end < len(text):
                search_start = int(end - max_chars * 0.2)
                sentence_break = max(
                    text[search_start:end].rfind('. '),
                    text[search_start:end].rfind('! '),
                    text[search_start:end].rfind('? ')
                )

                if sentence_break > 0:
                    end = search_start + sentence_break + 1
                else:
                    # Fall back to word boundary
                    space_break = text[search_start:end].rfind(' ')
                    if space_break > 0:
                        end = search_start + space_break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = end - overlap if end < len(text) else end

            # Safety check to prevent infinite loop
            if start >= len(text):
                break

        return chunks

    def generate_summary(self, dialogue: str, max_length: Optional[int] = None) -> str:
        """
        Generate summary using fine-tuned FLAN-T5 model

        Generation parameters optimized for your model's performance:
        - num_beams=4: Beam search for better quality
        - no_repeat_ngram_size=3: Prevent repetition
        - length_penalty=1.0: Balanced length control
        - early_stopping=True: Stop when all beams finish

        Args:
            dialogue: Input dialogue/transcript text
            max_length: Maximum length of summary (uses default if None)

        Returns:
            Generated summary string
        """
        if not TORCH_AVAILABLE:
            return "Summary service unavailable - PyTorch not properly installed"

        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not loaded. Please initialize the service first.")

        if max_length is None:
            max_length = self.max_output_length

        try:
            # Format input
            input_text = self.format_input(dialogue)

            # Tokenize with truncation
            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                max_length=self.max_input_length,
                truncation=True,
                padding=True
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate with optimized parameters
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=4,
                    early_stopping=True,
                    no_repeat_ngram_size=3,
                    length_penalty=1.0,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )

            # Decode
            summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            return summary.strip()

        except Exception as e:
            logger.error(f"❌ Error generating summary: {e}")
            raise RuntimeError(f"Failed to generate summary: {e}")

    def generate_chunked_summary(self, text: str) -> str:
        """
        Generate summary for long transcripts by processing in chunks

        Process:
        1. Split transcript into overlapping chunks
        2. Summarize each chunk independently
        3. Combine chunk summaries
        4. If combined summary is still long, summarize again

        Args:
            text: Input text to summarize

        Returns:
            Combined summary from all chunks
        """
        text_length = len(text)
        word_count = len(text.split())

        logger.info(f"📊 Input: {word_count} words ({text_length} chars)")

        # If text is short enough, process directly
        if text_length <= self.chunk_size:
            logger.info("📝 Processing as single chunk")
            return self.generate_summary(text)

        # Split into chunks
        chunks = self.chunk_text(text, max_chars=self.chunk_size, overlap=self.chunk_overlap)
        logger.info(f"🔪 Split into {len(chunks)} chunks")

        # Summarize each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks, 1):
            chunk_words = len(chunk.split())
            logger.info(f"📋 Processing chunk {i}/{len(chunks)} ({chunk_words} words)...")

            try:
                chunk_summary = self.generate_summary(chunk)

                # Only keep summaries with meaningful content
                if chunk_summary and len(chunk_summary.split()) >= 5:
                    chunk_summaries.append(chunk_summary)
                    logger.info(f"✅ Chunk {i} summarized: {len(chunk_summary.split())} words")
                else:
                    logger.warning(f"⚠️  Chunk {i} produced short summary, skipping")

            except Exception as e:
                logger.error(f"❌ Error processing chunk {i}: {e}")
                continue

        if not chunk_summaries:
            return "Error: Could not generate summary from any chunk"

        # Combine summaries
        if len(chunk_summaries) == 1:
            combined = chunk_summaries[0]
        else:
            # Join with proper spacing
            combined = " ".join(s.strip() for s in chunk_summaries)

            # If combined is still very long, summarize again
            if len(combined.split()) > 300:
                logger.info(f"🔄 Combined summary too long ({len(combined.split())} words), re-summarizing...")
                try:
                    combined = self.generate_summary(combined)
                except Exception as e:
                    logger.warning(f"⚠️  Could not re-summarize, using concatenated version: {e}")

        # Clean up formatting
        combined = combined.replace('..', '.').replace('  ', ' ').strip()

        # Log statistics
        final_words = len(combined.split())
        compression_ratio = final_words / word_count
        logger.info(f"📏 Final: {final_words} words ({compression_ratio:.1%} compression)")

        return combined

    def parse_structured_output(self, summary: str) -> Dict[str, Any]:
        """
        Parse structured output from model into components

        Expected format:
        Attendees: [list]
        Key Points:
        - [point 1]
        - [point 2]
        Decisions Made:
        - [decision 1]
        Action Items:
        - [action 1]

        Args:
            summary: Raw summary text from model

        Returns:
            Dictionary with parsed components
        """
        result = {
            "summary": summary,
            "attendees": [],
            "key_points": [],
            "decisions": [],
            "action_items": []
        }

        try:
            # Extract Attendees
            attendees_match = re.search(r'Attendees?:\s*([^\n]+)', summary, re.IGNORECASE)
            if attendees_match:
                attendees_text = attendees_match.group(1)
                result["attendees"] = [a.strip() for a in re.split(r'[,;]', attendees_text) if a.strip()]

            # Extract Key Points
            key_points_section = re.search(
                r'Key Points?:(.*?)(?:Decisions?|Action Items?|$)',
                summary,
                re.IGNORECASE | re.DOTALL
            )
            if key_points_section:
                points_text = key_points_section.group(1)
                points = re.findall(r'[-•]\s*([^\n]+)', points_text)
                result["key_points"] = [p.strip() for p in points if p.strip()]

            # Extract Decisions
            decisions_section = re.search(
                r'Decisions? Made:(.*?)(?:Action Items?|$)',
                summary,
                re.IGNORECASE | re.DOTALL
            )
            if decisions_section:
                decisions_text = decisions_section.group(1)
                decisions = re.findall(r'[-•]\s*([^\n]+)', decisions_text)
                result["decisions"] = [d.strip() for d in decisions if d.strip()]

            # Extract Action Items
            action_items_section = re.search(
                r'Action Items?:(.*?)$',
                summary,
                re.IGNORECASE | re.DOTALL
            )
            if action_items_section:
                items_text = action_items_section.group(1)
                items = re.findall(r'[-•]\s*([^\n]+)', items_text)
                result["action_items"] = [i.strip() for i in items if i.strip()]

        except Exception as e:
            logger.warning(f"⚠️  Error parsing structured output: {e}")

        return result

    def generate_meeting_summary(self, transcript: str) -> Dict[str, Any]:
        """
        Generate a comprehensive structured meeting summary

        Main entry point for meeting summarization with full structured output

        Args:
            transcript: Meeting transcript text

        Returns:
            Dictionary containing:
            - summary: Full summary text
            - attendees: List of attendees
            - key_points: List of key discussion points
            - decisions: List of decisions made
            - action_items: List of action items
            - status: success/error
            - metrics: Performance metrics
        """
        try:
            logger.info(f"📝 Starting structured summary generation for {len(transcript.split())} words")

            # Generate summary using chunked processing
            raw_summary = self.generate_chunked_summary(transcript)

            # Parse structured components
            parsed = self.parse_structured_output(raw_summary)

            # Calculate metrics
            original_words = len(transcript.split())
            summary_words = len(raw_summary.split())

            return {
                "status": "success",
                "summary": parsed["summary"],
                "attendees": parsed["attendees"],
                "key_points": parsed["key_points"],
                "decisions": parsed["decisions"],
                "action_items": parsed["action_items"],
                "metrics": {
                    "original_words": original_words,
                    "summary_words": summary_words,
                    "compression_ratio": summary_words / original_words if original_words > 0 else 0,
                    "model": "flan-t5-base-finetuned",
                    "device": str(self.device)
                }
            }

        except Exception as e:
            logger.error(f"❌ Error generating meeting summary: {e}")
            return {
                "status": "error",
                "summary": None,
                "attendees": [],
                "key_points": [],
                "decisions": [],
                "action_items": [],
                "error": str(e)
            }

    def generate_simple_meeting_summary(self, transcript: str) -> str:
        """
        Generate a simple meeting summary (text only, no structured parsing)

        This is the backward-compatible entry point for existing API endpoints

        Args:
            transcript: Meeting transcript text

        Returns:
            Summary string
        """
        try:
            logger.info(f"📝 Starting simple summary generation for {len(transcript.split())} words")

            # Use chunked processing for optimal results
            summary = self.generate_chunked_summary(transcript)

            logger.info(f"✅ Summary generated successfully")
            return summary

        except Exception as e:
            logger.error(f"❌ Error generating simple meeting summary: {e}")
            return f"Error generating summary: {str(e)}"

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model

        Returns:
            Dictionary with model information
        """
        if not self.model:
            return {"status": "not_loaded"}

        param_count = sum(p.numel() for p in self.model.parameters())

        return {
            "status": "loaded",
            "model_path": self.model_path,
            "device": str(self.device),
            "parameters": param_count,
            "parameters_millions": round(param_count / 1e6, 1),
            "max_input_length": self.max_input_length,
            "max_output_length": self.max_output_length,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap
        }


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
    if not TORCH_AVAILABLE:
        return "Summary service unavailable - PyTorch not properly installed"

    service = get_summarization_service()
    return service.generate_summary(text, **kwargs)


def generate_meeting_summary(transcript: str) -> Dict[str, Any]:
    """Convenience function to generate a structured meeting summary"""
    if not TORCH_AVAILABLE:
        return {
            "status": "error",
            "summary": "Summary service unavailable - PyTorch not properly installed",
            "attendees": [],
            "key_points": [],
            "decisions": [],
            "action_items": [],
            "error": "PyTorch dependencies not available"
        }

    service = get_summarization_service()
    return service.generate_meeting_summary(transcript)


def generate_simple_meeting_summary(transcript: str) -> str:
    """Convenience function to generate a simple meeting summary (text only)"""
    if not TORCH_AVAILABLE:
        return "Summary service unavailable - PyTorch not properly installed"

    service = get_summarization_service()
    return service.generate_simple_meeting_summary(transcript)

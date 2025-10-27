"""
Summarization service using fine-tuned FLAN-T5 model
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel, PeftConfig
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SummarizationService:
    """
    Service for generating summaries using a fine-tuned FLAN-T5 model with LoRA adapters
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the summarization service
        
        Args:
            model_path: Path to the model weights directory
        """
        self.model_path = model_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "models", "weights"
        )
        self.model = None
        self.tokenizer = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_model()
    
    def _load_model(self):
        """Load the fine-tuned model and tokenizer"""
        try:
            logger.info(f"Loading model from {self.model_path}")
            
            # Check if model files exist
            config_path = os.path.join(self.model_path, "adapter_config.json")
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Adapter config not found at {config_path}")
            
            # Load PEFT config to get base model
            try:
                peft_config = PeftConfig.from_pretrained(self.model_path)
                base_model_name = peft_config.base_model_name_or_path
                logger.info(f"Using base model: {base_model_name}")
            except Exception as e:
                logger.error(f"Error loading PEFT config: {e}")
                # Fallback to default base model if config loading fails
                base_model_name = "google/flan-t5-base"
                logger.warning(f"Falling back to default base model: {base_model_name}")
            
            # Load base model and tokenizer
            logger.info("Loading base model and tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(base_model_name)
            
            # Ensure pad token is set
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            base_model = AutoModelForSeq2SeqLM.from_pretrained(
                base_model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True
            )
            
            # Load the fine-tuned adapters
            logger.info("Loading fine-tuned adapters...")
            try:
                self.model = PeftModel.from_pretrained(
                    base_model, 
                    self.model_path,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
                )
            except Exception as e:
                logger.error(f"Error loading PEFT adapters: {e}")
                logger.warning("Falling back to base model without adapters")
                self.model = base_model
            
            # Move to device if not using device_map
            if not torch.cuda.is_available():
                self.model = self.model.to(self.device)
            
            # Set model to evaluation mode
            self.model.eval()
            
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise RuntimeError(f"Failed to load summarization model: {e}")
    
    def _preprocess_input(self, text: str) -> str:
        """
        Preprocess input text for summarization
        
        Args:
            text: Raw input text
            
        Returns:
            Formatted text for the model
        """
        # Add the summarization prefix
        if not text.startswith("summarize:"):
            text = f"summarize: {text}"
        
        return text
    
    def _format_meeting_transcript(self, transcript: str) -> str:
        """
        Format meeting transcript for better summarization
        
        Args:
            transcript: Raw meeting transcript
            
        Returns:
            Formatted transcript
        """
        # Use a simpler, more direct prompt for better results
        formatted_prompt = (
            f"Summarize this meeting transcript in 2-3 sentences. "
            f"Include key points and decisions: {transcript}"
        )
        
        return self._preprocess_input(formatted_prompt)
    
    def generate_summary(
        self, 
        text: str, 
        max_length: int = 200,
        min_length: int = 30,
        temperature: float = 0.3,
        do_sample: bool = False,
        num_beams: int = 4,
        repetition_penalty: float = 1.3,
        no_repeat_ngram_size: int = 3,
        length_penalty: float = 1.2,
        diversity_penalty: float = 0.0,
        num_beam_groups: int = 1,
        is_meeting_transcript: bool = False
    ) -> str:
        """
        Generate summary for the given text
        
        Args:
            text: Input text to summarize
            max_length: Maximum length of the summary
            min_length: Minimum length of the summary
            temperature: Sampling temperature
            do_sample: Whether to use sampling
            num_beams: Number of beams for beam search
            is_meeting_transcript: Whether the input is a meeting transcript
            
        Returns:
            Generated summary
        """
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not loaded. Please initialize the service first.")
        
        try:
            # Format input based on type
            if is_meeting_transcript:
                formatted_input = self._format_meeting_transcript(text)
            else:
                formatted_input = self._preprocess_input(text)
            
            # Tokenize input
            inputs = self.tokenizer(
                formatted_input,
                return_tensors="pt",
                max_length=1024,
                truncation=True,
                padding=True
            ).to(self.device)
            
            # Build generation kwargs while enforcing valid parameter combinations
            gen_kwargs = dict(
                max_length=max_length,
                min_length=min_length,
                temperature=temperature,
                do_sample=do_sample,
                early_stopping=True,
                pad_token_id=self.tokenizer.eos_token_id,
                repetition_penalty=repetition_penalty,
                no_repeat_ngram_size=no_repeat_ngram_size,
                length_penalty=length_penalty,
            )

            # Enforce transformers' constraints:
            # - If sampling (do_sample=True) then diversity_penalty must be 0.0 and num_beams should be 1
            # - If using diversity_penalty or beam groups, do_sample must be False
            if do_sample:
                # sampling mode: disable diversity and use single beam
                gen_kwargs["diversity_penalty"] = 0.0
                effective_num_beams = 1
                gen_kwargs["num_beams"] = effective_num_beams
            else:
                # beam/search mode: allow diversity and beam groups
                gen_kwargs["diversity_penalty"] = float(diversity_penalty)
                # ensure num_beam_groups is valid
                if num_beam_groups < 1:
                    num_beam_groups = 1
                # transformers requires num_beams % num_beam_groups == 0
                if num_beams % num_beam_groups != 0:
                    # fallback to single group
                    num_beam_groups = 1
                gen_kwargs["num_beams"] = num_beams
                gen_kwargs["num_beam_groups"] = num_beam_groups

            # Generate summary
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **gen_kwargs
                )
            
            # Decode the output
            summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Clean up the summary (remove input prefix if present)
            if summary.startswith("summarize:"):
                summary = summary[10:].strip()
            
            # Remove repetitive sentences for better quality
            summary = self._remove_repetitive_sentences(summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            raise RuntimeError(f"Failed to generate summary: {e}")
    
    def generate_meeting_summary(self, transcript: str) -> Dict[str, Any]:
        """
        Generate a comprehensive meeting summary with key points and action items
        
        Args:
            transcript: Meeting transcript text
            
        Returns:
            Dictionary containing summary and action items
        """
        try:
            # Generate main summary with better prompting
            main_summary = self.generate_summary(
                transcript,
                max_length=200,
                min_length=50,
                do_sample=False,  # Deterministic generation
                num_beams=4,
                is_meeting_transcript=True
            )
            
            return {
                "summary": main_summary,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error generating meeting summary: {e}")
            return {
                "summary": None,
                "status": "error",
                "error": str(e)
            }
    
    def generate_simple_meeting_summary(self, transcript: str) -> str:
        """
        Generate just a simple meeting summary (no extra fields)
        
        Args:
            transcript: Meeting transcript text
            
        Returns:
            Summary string
        """
        try:
            # Calculate appropriate summary length based on input length
            input_words = len(transcript.split())
            
            # Aim for 25-35% compression ratio for better coverage
            if input_words < 200:
                # Short transcripts: keep most content
                target_summary_words = max(50, int(input_words * 0.6))
            elif input_words < 500:
                # Medium transcripts: moderate compression
                target_summary_words = max(100, int(input_words * 0.4))
            else:
                # Long transcripts: aim for 30% retention
                target_summary_words = max(150, min(600, int(input_words * 0.3)))
            
            # Convert words to approximate tokens (multiply by 1.4 for better coverage)
            max_length = int(target_summary_words * 1.4)
            min_length = max(80, int(target_summary_words * 0.7))
            
            # Use a more comprehensive prompt
            formatted_prompt = (
                "Please provide a comprehensive and detailed summary of the following meeting discussion, "
                "including key points, decisions, and important details: "
                f"{transcript}"
            )
            
            summary = self.generate_summary(
                formatted_prompt,
                max_length=max_length,
                min_length=min_length,
                do_sample=False,  # Use beam search for more coherent longer summaries
                temperature=0.7,
                num_beams=4,
                repetition_penalty=1.2,  # Slightly lower to allow some natural repetition
                length_penalty=1.0  # Neutral length penalty for balanced output
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating simple meeting summary: {e}")
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
        # Estimate max_length based on words (rough approximation)
        max_length = min(max_words * 2, 200)  # tokens ≈ words * 1.3-2
        min_length = max(10, max_words // 4)
        
        return self.generate_summary(
            text,
            max_length=max_length,
            min_length=min_length,
            temperature=0.5,
            num_beams=3
        )
    
    def _remove_repetitive_sentences(self, text: str) -> str:
        """
        Remove repetitive sentences from the summary
        
        Args:
            text: Input text to clean
            
        Returns:
            Cleaned text with reduced repetition
        """
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        unique_sentences = []
        seen_sentences = set()
        
        for sentence in sentences:
            # Normalize sentence for comparison (lowercase, remove extra spaces)
            normalized = ' '.join(sentence.lower().split())
            
            # Check if this sentence is too similar to any previous sentence
            is_repetitive = False
            for seen in seen_sentences:
                # Calculate simple similarity (shared words ratio)
                words1 = set(normalized.split())
                words2 = set(seen.split())
                if len(words1) > 0 and len(words2) > 0:
                    similarity = len(words1.intersection(words2)) / len(words1.union(words2))
                    if similarity > 0.7:  # 70% similarity threshold
                        is_repetitive = True
                        break
            
            if not is_repetitive:
                unique_sentences.append(sentence)
                seen_sentences.add(normalized)
        
        return '. '.join(unique_sentences) + ('.' if unique_sentences else '')


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
    service = get_summarization_service()
    return service.generate_meeting_summary(transcript)


def generate_simple_meeting_summary(transcript: str) -> str:
    """Convenience function to generate a simple meeting summary (just text)"""
    service = get_summarization_service()
    return service.generate_simple_meeting_summary(transcript)
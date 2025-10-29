#!/usr/bin/env python3
"""
FLAN-T5 Meeting Summarizer - Inference Script (Updated for Latest Model)
Compatible with models trained using the fixed training script
"""

import os
import torch
from transformers import AutoTokenizer, T5ForConditionalGeneration
from peft import PeftModel
import warnings
warnings.filterwarnings("ignore")

class MeetingSummarizer:
    def __init__(self, model_path=None, lora_adapter_path=None, base_model="google/flan-t5-large"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🖥️  Using device: {self.device}")
        print(f"📊 Base model: {base_model} (780M params for superior quality)")
        
        # UPDATED: Use AutoTokenizer for compatibility
        if model_path and os.path.exists(model_path):
            print(f"📚 Loading tokenizer from: {model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        elif lora_adapter_path and os.path.exists(lora_adapter_path):
            print(f"📚 Loading tokenizer from: {lora_adapter_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(lora_adapter_path)
        else:
            print(f"📚 Loading base tokenizer: {base_model}")
            self.tokenizer = AutoTokenizer.from_pretrained(base_model)
        
        # Ensure pad token is set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load model
        if lora_adapter_path and os.path.exists(lora_adapter_path):
            print(f"🤖 Loading base model: {base_model}")
            print(f"🔧 Loading LoRA adapter from: {lora_adapter_path}")
            
            # Load base model
            self.model = T5ForConditionalGeneration.from_pretrained(
                base_model,
                torch_dtype=torch.float32,  # Use float32 for stability in inference
                device_map="auto" if self.device == "cuda" else None
            )
            
            # Load LoRA adapter
            self.model = PeftModel.from_pretrained(self.model, lora_adapter_path)
            print("✅ LoRA adapter loaded successfully")
            
        elif model_path and os.path.exists(model_path):
            print(f"🤖 Loading full fine-tuned model from: {model_path}")
            self.model = T5ForConditionalGeneration.from_pretrained(
                model_path,
                torch_dtype=torch.float32,  # Use float32 for stability
                device_map="auto" if self.device == "cuda" else None
            )
            print("✅ Full model loaded successfully")
            
        else:
            raise ValueError("Either model_path or lora_adapter_path must be provided and exist")
        
        # Move model to device and set to eval mode
        if self.device == "cpu":
            self.model = self.model.to(self.device)
        self.model.eval()
        
        print(f"✅ Model ready for inference")
        
        # Match training script settings - UPGRADED for longer, detailed summaries
        self.max_source_length = 512
        self.max_target_length = 300  # Increased from 128 to 300 for detailed summaries
    
    def format_input(self, dialogue):
        """Simplified format matching the proven working example"""
        return f"Summarize the following dialogue in third-person narrative form, removing all speaker tags, and focusing on the emotions and actions expressed and focusing only on important events and personal updates. Avoid repetition. meeting participants are absir ahmed khan and rihab rabbani:\n\n {dialogue}"

    def chunk_text(self, text, max_words=300):
        """Split text into meaningful chunks preserving dialogue structure"""
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
    
    def generate_chunked_summary(self, text, max_chunk_words=300):
        """Generate summary for large text by processing in chunks"""
        total_words = len(text.split())
        print(f"📊 Input: {total_words} words")
        
        if total_words <= max_chunk_words:
            print("📝 Processing as single chunk")
            return self.generate_summary(text)
        
        # Split into chunks
        chunks = self.chunk_text(text, max_chunk_words)
        print(f"🔪 Split into {len(chunks)} chunks")
        
        summaries = []
        for i, chunk in enumerate(chunks, 1):
            chunk_words = len(chunk.split())
            print(f"📋 Processing chunk {i}/{len(chunks)} ({chunk_words} words)...")
            
            try:
                chunk_summary = self.generate_summary(chunk)
                if chunk_summary and len(chunk_summary.split()) >= 5:
                    summaries.append(chunk_summary)
                    print(f"✅ Chunk {i} summary: {len(chunk_summary.split())} words")
                else:
                    print(f"⚠️ Chunk {i} produced short summary, skipping")
            except Exception as e:
                print(f"❌ Error processing chunk {i}: {e}")
        
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
        print(f"📏 Final summary: {combined_words} words ({compression_ratio:.1%} compression)")
        
        return combined
    
    def generate_summary(self, dialogue, max_length=None):
        """Generate summary with settings matching training"""
        if max_length is None:
            max_length = self.max_target_length
            
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
        min_length = max(80, min(int(max_length * 0.4), int(input_words * 0.3)))  # Minimum 80 words
        
        # Generate with UPGRADED settings for longer, detailed summaries
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=200,
                num_beams=4,                # reduce beams — less overfitting
                repetition_penalty=2.5,     # strong penalty for repeats
                no_repeat_ngram_size=4,     # prevent 4-word repetition
                length_penalty=0.9,         # avoid excessive length
                early_stopping=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        
        # Decode
        summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        sentences = summary.split('. ')
        unique_summary = '. '.join(dict.fromkeys(sentences))
        return unique_summary.strip()
    
    def interactive_mode(self):
        """Interactive mode for quick testing"""
        print("\n" + "="*60)
        print("Meeting Summarizer - Interactive Mode")
        print("="*60)
        print("Commands:")
        print("  • Type dialogue to summarize")
        print("  • 'quit' or 'exit' to quit")
        print("  • 'help' for examples")
        print("="*60)
        
        while True:
            user_input = input("\n💬 Enter dialogue: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            elif user_input.lower() == 'help':
                print("\n📝 Example dialogue format:")
                print("alice: we need to review the quarterly results")
                print("bob: i agree, revenue is up 15%")
                print("alice: great, let's present this to the board")
                continue
            elif not user_input:
                continue
            
            try:
                print("\n⏳ Generating summary...")
                summary = self.generate_summary(user_input)
                print(f"\n📋 Summary: {summary}")
                print(f"📊 ({len(user_input.split())} words → {len(summary.split())} words)")
            except Exception as e:
                print(f"❌ Error: {e}")

def find_model():
    """Find trained models with priority order"""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    paths = [
        # Current directory (weights folder)
        script_dir,
        
        # Local paths relative to script
        os.path.join(script_dir, "lora-adapter"),
        os.path.join(script_dir, "fine-tuned-flan-t5-meeting"),
        
        # Parent directory
        os.path.dirname(script_dir),
        
        # Common locations
        "./lora-adapter",
        "./fine-tuned-flan-t5-meeting",
        "./weights",
        
        # Legacy Kaggle paths (if running on Kaggle)
        "/kaggle/working/lora-adapter",
        "/kaggle/working/fine-tuned-flan-t5-meeting",
    ]
    
    found = {"lora": None, "full": None}
    
    print("\n🔍 Searching for trained models...")
    for path in paths:
        if os.path.exists(path):
            # Check if it's actually a valid model directory
            has_config = os.path.exists(os.path.join(path, "config.json"))
            has_adapter = os.path.exists(os.path.join(path, "adapter_config.json"))
            
            if has_adapter:
                found["lora"] = path
                print(f"✅ Found LoRA adapter: {path}")
            elif has_config:
                found["full"] = path
                print(f"✅ Found full model: {path}")
    
    # Show which will be used
    if found["lora"]:
        print(f"\n🎯 Will use LoRA adapter: {found['lora']} (recommended)")
    elif found["full"]:
        print(f"\n🎯 Will use full model: {found['full']}")
    else:
        print("\n❌ No trained models found!")
    
    return found

def main():
    print("="*60)
    print("FLAN-T5 Meeting Summarizer (Updated)")
    print("="*60)
    
    found_models = find_model()
    
    if not found_models["lora"] and not found_models["full"]:
        print("\n❌ No trained model found!")
        print("\n📝 Please run the training script first to create a model.")
        print("\n💡 This will create either:")
        print("   • /kaggle/working/lora-adapter (LoRA adapter - recommended)")
        print("   • /kaggle/working/fine-tuned-flan-t5-meeting (full model)")
        return
    
    try:
        print("\n🚀 Loading model...")
        summarizer = MeetingSummarizer(
            model_path=found_models["full"],
            lora_adapter_path=found_models["lora"]
        )
        
        print("\n" + "="*60)
        print("📋 Choose input method:")
        print("="*60)
        print("1. Interactive mode (chat-like interface)")
        print("2. Single summary (one-time)")
        print("3. Summarize file contents")
        print("="*60)
        
        choice = input("\n👉 Choice (1-3): ").strip()
        
        if choice == "1":
            summarizer.interactive_mode()
            
        elif choice == "2":
            print("\n💬 Enter your dialogue (press Enter twice when done):")
            print("Example: alice: let's discuss the budget\\nbob: i think we need more funds")
            lines = []
            while True:
                line = input()
                if line:
                    lines.append(line)
                else:
                    break
            
            dialogue = '\n'.join(lines)
            if dialogue:
                print("\n⏳ Generating summary...")
                summary = summarizer.generate_summary(dialogue)
                print(f"\n📋 Summary:\n{summary}")
                print(f"\n📊 Statistics:")
                print(f"   Input:  {len(dialogue.split())} words")
                print(f"   Output: {len(summary.split())} words")
            else:
                print("No input provided.")
                
        elif choice == "3":
            file_path = input("\n📁 Enter file path: ").strip()
            if not file_path or not os.path.exists(file_path):
                print("❌ File not found!")
                return
                
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read().strip()
                
            if file_content:
                print(f"\n📊 File contains {len(file_content.split())} words")
                print("⏳ Generating summary...")
                
                # Use chunked processing for large files
                summary = summarizer.generate_chunked_summary(file_content)
                
                print(f"\n📋 Summary:\n{summary}")
                
                # Show statistics
                input_words = len(file_content.split())
                output_words = len(summary.split())
                ratio = output_words / input_words if input_words > 0 else 0
                
                print(f"\n📊 Statistics:")
                print(f"   Input:      {input_words} words")
                print(f"   Output:     {output_words} words")
                print(f"   Compression: {ratio:.1%}")
                
                # Optionally save
                save = input("\n💾 Save summary to file? (y/n): ").strip().lower()
                if save == 'y':
                    output_path = file_path.rsplit('.', 1)[0] + '_summary.txt'
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(summary)
                    print(f"✅ Saved to: {output_path}")
            else:
                print("❌ File is empty.")
        else:
            print("❌ Invalid choice")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
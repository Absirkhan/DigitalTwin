# Meeting Summarizer - Local Inference

## Setup

Your workspace structure:
```
modhal/
├── weights/                    # LoRA adapter files
│   ├── adapter_config.json
│   ├── adapter_model.safetensors
│   ├── tokenizer files...
│   └── loss_showing_inference.py
├── run_inference.py           # Simple CLI inference script
└── sample_transcript.txt      # Example transcript
```

## Quick Start

### 1. Install Dependencies

```bash
pip install torch transformers peft sentencepiece
```

### 2. Run Inference (Simple Method)

```bash
python run_inference.py \
  --input_file sample_transcript.txt \
  --output_file summary.txt
```

### 3. Run Interactive Mode

```bash
cd weights
python loss_showing_inference.py
```

Then choose option 1 for interactive mode, or option 3 to process a file.

## Usage Examples

### Example 1: Simple Command Line
```bash
# Process any text file
python run_inference.py \
  --input_file transcript.txt \
  --output_file result.txt
```

### Example 2: Custom Adapter Path
```bash
python run_inference.py \
  --input_file transcript.txt \
  --output_file result.txt \
  --adapter_path ./weights
```

### Example 3: Using the Full Script
```bash
cd weights
python loss_showing_inference.py
```
Choose:
- Option 1: Interactive chat-like mode
- Option 2: Single summary (paste text)
- Option 3: Summarize file contents

## Files

- `run_inference.py` - Simple CLI tool for quick inference
- `weights/loss_showing_inference.py` - Full-featured interactive script
- `sample_transcript.txt` - Example meeting transcript

## Notes

- The model will automatically download `google/flan-t5-large` on first run
- LoRA adapter weights are loaded from `./weights/` directory
- GPU will be used if available, otherwise CPU (slower but works)
- Summaries are typically 15-30% of original length

## Troubleshooting

**Error: "No trained model found"**
- Make sure you're in the correct directory
- Check that `weights/` contains `adapter_config.json` and `adapter_model.safetensors`

**Memory Issues**
- Use CPU mode: The script will automatically use CPU if CUDA is not available
- Process smaller text chunks

**Slow Inference**
- This is normal on CPU, expect 30-60 seconds per summary
- Consider using a GPU or smaller model

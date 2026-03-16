#!/bin/bash
# Setup script for Meeting Summarizer

echo "🚀 Setting up Meeting Summarizer..."
echo ""

# Check if pip3 is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Please install Python 3 first."
    exit 1
fi

echo "📦 Installing required packages..."
pip3 install torch transformers peft sentencepiece accelerate

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Quick Start:"
echo "  python3 run_inference.py --input_file sample_transcript.txt --output_file summary.txt"
echo ""
echo "📚 For more options, see README_INFERENCE.md"

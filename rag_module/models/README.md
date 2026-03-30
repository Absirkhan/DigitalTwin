# LLM Models Directory

This directory contains GGUF model files for the RAG system's response generation.

## Required Model

**Qwen2.5-0.5B-Instruct (Q4_K_M quantization)**

### Download Instructions

1. Visit Hugging Face model repository:
   ```
   https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF
   ```

2. Download the Q4_K_M quantized version:
   - File: `qwen2.5-0.5b-instruct-q4_k_m.gguf`
   - Size: ~400MB

3. Place the downloaded file in this directory:
   ```
   rag_module/models/qwen2.5-0.5b-instruct-q4_k_m.gguf
   ```

### Direct Download Link

```bash
# Using wget
wget https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf

# Using curl
curl -L -o qwen2.5-0.5b-instruct-q4_k_m.gguf \
  https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf
```

### Alternative: Using Hugging Face CLI

```bash
# Install huggingface-cli
pip install huggingface-hub

# Download model
huggingface-cli download Qwen/Qwen2.5-0.5B-Instruct-GGUF \
  qwen2.5-0.5b-instruct-q4_k_m.gguf \
  --local-dir models/
```

## Model Specifications

### Qwen2.5-0.5B-Instruct (Q4_K_M)

- **Parameters:** 500 million
- **Quantization:** Q4_K_M (4-bit mixed quantization)
- **Size:** ~400MB
- **Context window:** 32,768 tokens (we use 2150)
- **Architecture:** Qwen2.5 (transformer-based)
- **Best for:** Fast CPU inference, conversational AI

### Performance Characteristics

**CPU Inference (4 threads):**
- 200 tokens: ~3-4 seconds
- 300 tokens: ~5-6 seconds
- Time to first token (streaming): ~500-800ms

**Memory Usage:**
- Model in RAM: ~500MB
- Per-inference overhead: ~50MB
- Total: ~600MB peak

## Alternative Models (Optional)

### If Quality is Insufficient

**Qwen2.5-1.5B-Instruct (Q4_K_M):**
- File: `qwen2.5-1.5b-instruct-q4_k_m.gguf`
- Size: ~1GB
- Latency: 10-15s for 200 tokens (3x slower)
- Quality: Significantly better reasoning

Download:
```
https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf
```

### If Speed is Critical

**Qwen2.5-0.5B-Instruct (Q3_K_M):**
- File: `qwen2.5-0.5b-instruct-q3_k_m.gguf`
- Size: ~300MB
- Latency: ~2-3s for 200 tokens (30% faster)
- Quality: Slightly lower (more quantization artifacts)

## Troubleshooting

### Model Not Found Error

If you see:
```
FileNotFoundError: [Errno 2] No such file or directory: 'models/qwen2.5-0.5b-instruct-q4_k_m.gguf'
```

**Solution:**
1. Verify file is in `rag_module/models/` directory
2. Check filename matches exactly (case-sensitive)
3. Ensure file downloaded completely (400MB)

### Out of Memory Error

If you see:
```
RuntimeError: Failed to allocate memory
```

**Solution:**
1. Close other applications to free RAM
2. Try smaller model (Q3_K_M quantization)
3. Reduce `n_ctx` in config (lower context window)

### Slow Inference

If inference takes >10s for 200 tokens:

**Solution:**
1. Increase `n_threads` in config (try 6-8 threads)
2. Verify CPU not throttling (check temperatures)
3. Try Q3_K_M quantization (faster but lower quality)

## Model Version Management

The cache keys include model version to avoid stale responses:
- Model file change → Cache automatically invalidated
- No manual cache clearing needed

## License

Qwen2.5 models are licensed under Apache 2.0:
- Commercial use allowed
- Free for research and production
- See: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF

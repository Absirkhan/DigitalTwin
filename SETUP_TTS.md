# NeuTTS Nano Voice Cloning Setup Guide

This guide covers the complete setup process for the NeuTTS Nano voice cloning feature in DigitalTwin.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Dependencies](#system-dependencies)
3. [Python Dependencies](#python-dependencies)
4. [Installation Steps](#installation-steps)
5. [Configuration](#configuration)
6. [Using Voice Cloning](#using-voice-cloning)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.11+** (Required by NeuTTS Nano)
- **PostgreSQL** (Database must be running and migrated)
- **8GB+ RAM** recommended for model inference
- **Microphone access** (for recording voice samples)
- **Internet connection** (for initial model download)

---

## System Dependencies

### eSpeak NG Installation

NeuTTS Nano requires **eSpeak NG 1.52.0+** for phonemization (text-to-phoneme conversion).

#### Windows

1. **Download eSpeak NG**:
   - Visit [eSpeak NG Releases](https://github.com/espeak-ng/espeak-ng/releases)
   - Download the latest Windows installer (e.g., `espeak-ng-X64.msi`)

2. **Install**:
   - Run the installer
   - Default installation path: `C:\Program Files\eSpeak NG`
   - Check "Add to PATH" if available (optional)

3. **Set Environment Variables**:
   - Open System Properties → Environment Variables
   - Add two **User** or **System** variables:
     - `PHONEMIZER_ESPEAK_LIBRARY` = `C:\Program Files\eSpeak NG\libespeak-ng.dll`
     - `PHONEMIZER_ESPEAK_PATH` = `C:\Program Files\eSpeak NG`

   **Note**: The backend TTS service auto-detects these paths if installed at the default location.

4. **Verify Installation**:
   ```cmd
   "C:\Program Files\eSpeak NG\espeak-ng.exe" --version
   ```
   Should output version 1.52.0 or higher.

#### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install espeak-ng

# Verify installation
espeak-ng --version  # Should be 1.52.0+
```

#### macOS

```bash
brew install espeak-ng

# Verify installation
espeak-ng --version  # Should be 1.52.0+
```

---

## Python Dependencies

### 1. Install Standard Dependencies

First, install the base dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

This installs:
- `soundfile>=0.12.1` (Audio I/O)
- `torch>=2.0.0` (Already in requirements for FLAN-T5)
- All other project dependencies

### 2. Install NeuTTS Nano

NeuTTS Nano must be installed **manually from source**:

```bash
# Clone the NeuTTS repository
git clone https://github.com/neuphonic/neutts.git

# Install in editable mode
pip install -e ./neutts

# Install llama-cpp-python (required for GGUF model support)
pip install llama-cpp-python
```

**Why manual installation?**
- NeuTTS is not yet published to PyPI
- The project is under active development
- This ensures you get the latest version with GGUF support

### 3. Verify Installation

```python
python -c "from neutts import NeuTTS; print('NeuTTS installed successfully')"
```

If you see `ImportError`, check:
- NeuTTS repo was cloned correctly
- `pip install -e ./neutts` completed without errors
- `llama-cpp-python` is installed

---

## Installation Steps

### Step-by-Step Setup

1. **Activate Virtual Environment** (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

2. **Install eSpeak NG** (see [System Dependencies](#system-dependencies))

3. **Install Python Dependencies**:
   ```bash
   # Install base requirements
   pip install -r requirements.txt

   # Install NeuTTS Nano
   git clone https://github.com/neuphonic/neutts.git
   pip install -e ./neutts
   pip install llama-cpp-python
   ```

4. **Run Database Migrations** (if not already done):
   ```bash
   alembic upgrade head
   ```
   This adds the `has_voice_profile` column to the `users` table.

5. **Verify Backend Starts**:
   ```bash
   uvicorn app.main:app --reload
   ```
   Check for TTS-related logs:
   ```
   INFO:app.services.tts_service:TTS service initialized (model will load on first use)
   ```

6. **Access API Documentation**:
   - Open [http://localhost:8000/docs](http://localhost:8000/docs)
   - Verify `/api/v1/tts` endpoints are listed:
     - `POST /api/v1/tts/upload-voice`
     - `GET /api/v1/tts/voice-status`
     - `DELETE /api/v1/tts/voice`
     - `POST /api/v1/tts/synthesize`

---

## Configuration

### Environment Variables

No additional environment variables are required for basic TTS functionality. The service uses:

- **Voice Profile Storage**: `data/voice_profiles/{user_id}/`
  - `ref_codes.pt` — Encoded voice embeddings
  - `ref_text.txt` — Reference transcript

- **Model Storage**: Downloaded to Hugging Face cache (`~/.cache/huggingface/`)
  - Backbone: `neuphonic/neutts-nano-q4-gguf` (~200MB)
  - Codec: `neuphonic/neucodec` (~50MB)

### Directory Structure

After first use, the directory structure will be:

```
DigitalTwin/
├── data/
│   └── voice_profiles/
│       └── {user_id}/
│           ├── ref_codes.pt        # Voice encoding (PyTorch tensor)
│           └── ref_text.txt        # Reference transcript
├── neutts/                         # NeuTTS repository (if cloned locally)
└── ...
```

---

## Using Voice Cloning

### Frontend Workflow (User Perspective)

1. **Navigate to Profile Page**:
   - Log in to DigitalTwin
   - Go to **Dashboard → Profile**
   - Scroll to the **Voice Profile** section

2. **Record Voice Sample**:
   - Click **"Record Now (15 seconds)"**
   - Allow microphone access when prompted
   - Read the displayed script aloud:
     > "My name is [Your Name]. I use DigitalTwin to automate my meetings. When someone asks for my input, the system will respond on my behalf using this voice."
   - Recording auto-stops after 15 seconds (or click "Stop Recording")

3. **Confirm Transcript**:
   - Review the pre-filled reference text
   - Edit if needed to match what you actually said
   - Click **"Submit Voice Profile"**

4. **Alternative: Upload Audio File**:
   - Click **"Upload Audio File (.wav, .mp3)"**
   - Select a 10-15 second audio file
   - Confirm the transcript of what was said
   - Submit

5. **Manage Voice Profile**:
   - Once saved, you'll see a green "Voice profile active" badge
   - Click **"Re-record Voice"** to update your profile
   - Click **"Delete Voice Profile"** to remove it

### Backend API Usage

#### Check Voice Status

```bash
curl -X GET "http://localhost:8000/api/v1/tts/voice-status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Response:
{
  "has_voice_profile": true
}
```

#### Upload Voice Sample

```bash
curl -X POST "http://localhost:8000/api/v1/tts/upload-voice" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "audio_file=@voice_sample.wav" \
  -F "ref_text=My name is John. I use DigitalTwin..."

# Response:
{
  "success": true,
  "message": "Voice profile saved successfully"
}
```

#### Synthesize Speech (Testing)

```bash
curl -X POST "http://localhost:8000/api/v1/tts/synthesize" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "text=Hello, this is a test of my voice clone." \
  -o output.wav

# This saves the synthesized audio to output.wav
```

#### Delete Voice Profile

```bash
curl -X DELETE "http://localhost:8000/api/v1/tts/voice" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Response:
{
  "success": true,
  "message": "Voice profile deleted successfully"
}
```

---

## Troubleshooting

### Common Issues

#### 1. **"Failed to load NeuTTS model"**

**Symptom**: Backend logs show `ImportError: No module named 'neutts'`

**Solution**:
```bash
# Verify NeuTTS is installed
pip show neutts

# If not found, reinstall
git clone https://github.com/neuphonic/neutts.git
pip install -e ./neutts
pip install llama-cpp-python
```

#### 2. **"espeak-ng not found" or Phonemization Errors**

**Symptom**: Error during voice encoding: `FileNotFoundError: espeak-ng`

**Solution (Windows)**:
1. Install eSpeak NG from [GitHub releases](https://github.com/espeak-ng/espeak-ng/releases)
2. Set environment variables:
   ```cmd
   setx PHONEMIZER_ESPEAK_LIBRARY "C:\Program Files\eSpeak NG\libespeak-ng.dll"
   setx PHONEMIZER_ESPEAK_PATH "C:\Program Files\eSpeak NG"
   ```
3. Restart terminal and backend server

**Solution (Linux)**:
```bash
sudo apt install espeak-ng
espeak-ng --version  # Verify 1.52.0+
```

#### 3. **"Model download failed" or Timeout Errors**

**Symptom**: First TTS request times out or fails with network error

**Solution**:
- Ensure internet connection is stable
- Models are ~250MB total and download once
- Check Hugging Face is accessible: `https://huggingface.co/neuphonic`
- If behind proxy, set: `export HF_ENDPOINT=https://hf-mirror.com` (or your proxy)

#### 4. **"Microphone permission denied" (Frontend)**

**Symptom**: Browser shows "Permission denied" when clicking "Record Now"

**Solution**:
- Check browser permissions: Settings → Site Settings → Microphone
- Allow microphone access for `localhost:3000`
- Try a different browser (Chrome/Edge recommended)
- If on HTTPS, ensure secure context

#### 5. **"Voice upload failed: File too large"**

**Symptom**: Upload error with large audio files

**Solution**:
- Maximum file size: **10MB**
- Recommended: 10-15 seconds of audio at 24kHz/16-bit WAV
- Compress large files:
  ```bash
  ffmpeg -i large_file.wav -ar 24000 -ac 1 -b:a 128k compressed.wav
  ```

#### 6. **Reference Text is Required**

**Symptom**: Upload succeeds but synthesis quality is poor

**Why**: NeuTTS Nano uses the reference text as a conditioning prompt. Without an accurate transcript, the model degrades significantly.

**Solution**:
- Always provide the exact transcript of what was said in the audio
- If you don't remember, re-record using the provided script
- The default script is optimized for DigitalTwin's use case

#### 7. **Model Inference is Slow (>5 seconds per sentence)**

**Symptom**: Synthesis takes too long on CPU

**Solution**:
- NeuTTS Nano Q4 GGUF is optimized for CPU inference
- Expected latency: ~2-3 seconds for 1-2 sentences on modern CPUs
- For faster inference:
  - Use fewer words per synthesis call
  - Consider GPU support (requires CUDA-enabled `llama-cpp-python`)
  - Upgrade to a faster CPU (multi-core recommended)

#### 8. **Database Migration Failed**

**Symptom**: `alembic upgrade head` fails with `IntegrityError`

**Solution**:
This was fixed in the migration file. If you still see errors:
```bash
# Check current migration status
alembic current

# If stuck, rollback and re-migrate
alembic downgrade -1
alembic upgrade head
```

---

## Performance Notes

### Model Characteristics

- **Backbone Model**: NeuTTS Nano Q4 GGUF (~200MB)
  - Quantized to 4-bit for fast CPU inference
  - Runs on CPU without GPU
  - Expected latency: 2-3 seconds per sentence

- **Codec Model**: NeuCodec (~50MB)
  - Neural audio codec for high-quality reconstruction
  - 24kHz sample rate output

### Voice Profile Storage

- **Per-user storage**: ~500KB per voice profile
  - `ref_codes.pt`: ~300KB (PyTorch tensor)
  - `ref_text.txt`: <1KB (plain text)

### Memory Usage

- **Idle**: ~200MB (before model load)
- **First request**: ~1.5GB (model loading)
- **Subsequent requests**: ~800MB (model cached)

---

## Reference Text Importance

### Why Reference Text Matters

NeuTTS Nano is a **text-conditioned voice cloning model**. The reference text serves as a conditioning prompt that:

1. **Aligns audio with text**: Helps the model learn phoneme-to-audio mappings
2. **Improves prosody**: Captures speaking style, rhythm, and intonation
3. **Reduces hallucinations**: Prevents the model from generating incorrect sounds

**Without accurate reference text**, synthesis quality degrades by **30-50%** (measured by speaker similarity).

### Best Practices

1. **Use the provided script**:
   ```
   My name is [Your Name]. I use DigitalTwin to automate my meetings.
   When someone asks for my input, the system will respond on my behalf using this voice.
   ```

2. **Read naturally**: Don't rush or over-enunciate

3. **Match exactly**: Reference text must match what you actually said
   - Including filler words ("um", "uh") if present
   - Including pauses and hesitations

4. **Audio quality**:
   - Quiet environment (no background noise)
   - Clear pronunciation
   - Normal speaking volume
   - 10-15 seconds is ideal

---

## Future Integration

### Planned Features

1. **Auto-synthesis during meetings**:
   - When the bot needs to speak, automatically synthesize using the user's voice
   - Integrate with Recall.ai bot audio output

2. **Real-time synthesis**:
   - Stream audio chunks for lower latency
   - Use NeuTTS Nano's streaming GGUF support

3. **Voice profile versioning**:
   - Save multiple voice profiles per user
   - A/B test different recordings

4. **Quality metrics**:
   - Measure speaker similarity after upload
   - Provide feedback on recording quality

---

## Additional Resources

- **NeuTTS Nano Repository**: [https://github.com/neuphonic/neutts](https://github.com/neuphonic/neutts)
- **eSpeak NG Documentation**: [https://github.com/espeak-ng/espeak-ng](https://github.com/espeak-ng/espeak-ng)
- **Hugging Face Models**:
  - Backbone: [neuphonic/neutts-nano-q4-gguf](https://huggingface.co/neuphonic/neutts-nano-q4-gguf)
  - Codec: [neuphonic/neucodec](https://huggingface.co/neuphonic/neucodec)

---

## Support

If you encounter issues not covered in this guide:

1. Check backend logs: `uvicorn app.main:app --reload --log-level debug`
2. Check browser console (F12) for frontend errors
3. Verify database migration: `alembic current`
4. Test TTS endpoints in Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

For bug reports, create an issue with:
- OS and Python version
- Full error traceback
- Steps to reproduce

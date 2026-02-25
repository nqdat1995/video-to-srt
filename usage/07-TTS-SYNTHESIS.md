# TTS Audio Synthesis (Tổng hợp tiếng nói)

## Generate Audio from SRT Content

### cURL Example

```bash
curl -X POST "http://localhost:8000/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "srt_content": "1\n00:00:01,000 --> 00:00:05,000\nHello world\n\n2\n00:00:05,000 --> 00:00:10,000\nHow are you?\n",
    "tts_voice": "BV074_streaming",
    "output_filename": "output_audio.wav",
    "return_base64": true
  }'

# Response:
# {
#   "task_id": "550e8400-e29b...",
#   "status": "success",
#   "audio_filename": "output_audio.wav",
#   "audio_path": "/path/to/tts_output/output_audio.wav",
#   "audio_base64": "UklGRiY...",
#   "duration_ms": 9000,
#   "size_bytes": 144000,
#   "message": "Audio synthesis completed successfully"
# }
```

### Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `srt_content` | string | - | SRT text | SRT subtitle content (full text) |
| `tts_voice` | string | "BV074_streaming" | voice_id | Voice identifier |
| `output_filename` | string | auto | filename | Output audio filename |
| `return_base64` | bool | true | true/false | Return audio as base64 |

### Available Voices

- `BV074_streaming` - Default Vietnamese voice (natural, neutral)
- `BV104_streaming` - Alternative Vietnamese voice (slightly different tone)
- Other voices depend on TTS provider capabilities

## Python Client - Basic

```python
import requests
import base64
from pathlib import Path

srt_content = """1
00:00:01,000 --> 00:00:05,000
Xin chào thế giới

2
00:00:05,000 --> 00:00:10,000
Bạn khỏe không?
"""

response = requests.post(
    "http://localhost:8000/tts/generate",
    json={
        "srt_content": srt_content,
        "tts_voice": "BV074_streaming",
        "output_filename": "vietnamese_audio.wav",
        "return_base64": True
    }
)

if response.status_code == 200:
    result = response.json()
    print(f"Task ID: {result['task_id']}")
    print(f"Duration: {result['duration_ms']}ms")
    print(f"File size: {result['size_bytes']} bytes")
    
    # Save audio from base64
    if result.get("audio_base64"):
        audio_data = base64.b64decode(result["audio_base64"])
        output_file = Path("downloads") / result["audio_filename"]
        output_file.parent.mkdir(exist_ok=True)
        output_file.write_bytes(audio_data)
        print(f"Saved to: {output_file}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

## Python Client - From File

```python
import requests
from pathlib import Path

# Load SRT from file
srt_content = Path("subtitles.srt").read_text(encoding="utf-8")

response = requests.post(
    "http://localhost:8000/tts/generate",
    json={
        "srt_content": srt_content,
        "tts_voice": "BV074_streaming",
        "output_filename": "output.wav"
    }
)

result = response.json()
audio_path = result["audio_path"]
print(f"Audio generated: {audio_path}")
```

## Complete Workflow: Extract → TTS → Combine

```python
import requests
import os
from pathlib import Path

# Step 1: Extract SRT from video
print("Step 1: Extracting subtitles...")
extract_resp = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": "input_video.mp4",
        "lang": "vi"
    }
)
srt_content = extract_resp.json()["srt"]

# Step 2: Generate audio from extracted SRT
print("Step 2: Synthesizing audio...")
tts_resp = requests.post(
    "http://localhost:8000/tts/generate",
    json={
        "srt_content": srt_content,
        "tts_voice": "BV074_streaming",
        "output_filename": "synthesized_audio.wav",
        "return_base64": False
    }
)

audio_path = tts_resp.json()["audio_path"]
print(f"Audio created: {audio_path}")

# Step 3: Combine original video + synthesized audio
print("Step 3: Combining video + audio...")
output_file = "output_with_audio.mp4"
os.system(f"""ffmpeg -i input_video.mp4 -i "{audio_path}" \\
  -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 "{output_file}" -y""")

print(f"✓ Complete! Output: {output_file}")
```

## Advanced Options

### Custom Voice and Output Directory

```python
import requests

response = requests.post(
    "http://localhost:8000/tts/generate",
    json={
        "srt_content": open("subtitles.srt").read(),
        "tts_voice": "BV104_streaming",  # Different voice
        "output_filename": "custom_output.wav",
        "return_base64": False  # Don't return base64 for large files
    }
)

result = response.json()
audio_path = result["audio_path"]
print(f"Audio file: {audio_path}")
```

### Batch Audio Generation

```python
import requests
from pathlib import Path
import concurrent.futures

def generate_audio(srt_file):
    """Generate audio for one SRT file"""
    srt_content = Path(srt_file).read_text(encoding="utf-8")
    
    response = requests.post(
        "http://localhost:8000/tts/generate",
        json={
            "srt_content": srt_content,
            "tts_voice": "BV074_streaming",
            "output_filename": Path(srt_file).stem + ".wav"
        }
    )
    
    if response.status_code == 200:
        return response.json()["audio_path"]
    return None

# Process multiple SRT files in parallel
srt_files = list(Path("subtitles").glob("*.srt"))

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(generate_audio, srt_files))

print(f"Generated {len([r for r in results if r])} audio files")
```

## Configuration

Set these environment variables in `.env`:

```bash
# TTS Settings
TTS_ENABLED=true
TTS_API_KEY=ddjeqjLGMn
TTS_API_TOKEN=your_api_token_here
TTS_DEFAULT_VOICE=BV074_streaming
TTS_OUTPUT_DIR=./tts_output
TTS_TEMP_DIR=./tts_temp
TTS_BATCH_SIZE=1000
TTS_MAX_RETRIES=3
```

## Response Models

### Success Response

```json
{
  "task_id": "string",         # Task UUID
  "status": "success",          # Operation status
  "audio_filename": "string",   # Output filename
  "audio_path": "string",       # Full file path on server
  "audio_base64": "string",     # Base64 encoded audio (optional)
  "duration_ms": 9000,          # Audio duration in milliseconds
  "size_bytes": 144000,         # File size in bytes
  "message": "string"           # Optional message
}
```

### Error Response

```json
{
  "status": "failed",
  "error": "Invalid SRT content",
  "message": "TTS service error details..."
}
```

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| TTS service disabled | TTS_ENABLED=false | Set TTS_ENABLED=true in .env |
| Invalid SRT content | Malformed SRT | Validate SRT format |
| Empty SRT | No subtitle text | Check SRT content is not empty |
| API authentication failed | Invalid API key/token | Check TTS_API_KEY and TTS_API_TOKEN |
| Output directory error | Can't write to disk | Check TTS_OUTPUT_DIR permissions |

## Performance

| Task | Time | Notes |
|------|------|-------|
| 1 minute audio | 2-5 seconds | TTS processing |
| 10 minutes audio | 20-50 seconds | Depends on text length |
| Return base64 | +500ms | Encoding overhead |

See [09-TROUBLESHOOTING.md](09-TROUBLESHOOTING.md) for detailed troubleshooting.

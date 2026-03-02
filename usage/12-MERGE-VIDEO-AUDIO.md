# Merge Video with Audio API

This guide explains how to use the `/merge-video` endpoint to combine a video file with an audio file (e.g., from TTS synthesis).

## Overview

The merge API allows you to:
- Merge a video file with an audio file (from TTS or other sources)
- Control the volume level of the video's original audio (0-100)
- Optionally scale the audio duration to match the video duration using pitch-preserving time-stretching

## Prerequisites

1. An uploaded video file (obtained from `/upload-video` endpoint) with its `video_id`
2. An audio file (from `/tts/generate` endpoint) with its `audio_id`
3. FFmpeg installed on the system with audio/video codec support

## Workflow

### Step 1: Upload Video

Upload your source video file using the `/upload-video` endpoint:

```bash
curl -X POST http://localhost:8000/upload-video \
  -F "file=@input_video.mp4" \
  -H "Content-Type: multipart/form-data"
```

Response:
```json
{
  "id": "uuid-video-id",
  "user_id": "user-123",
  "filename": "input_video.mp4",
  "file_size": 5242880,
  "created_at": "2025-02-28T10:00:00",
  "status": "success",
  "message": null
}
```

Save the `id` (video_id) for use in the merge endpoint.

### Step 2: Generate Audio via TTS

Generate audio from subtitles using the `/tts/generate` endpoint:

```bash
curl -X POST http://localhost:8000/tts/generate \
  -H "Content-Type: application/json" \
  -d '{
    "srt_content": "1\n00:00:00,000 --> 00:00:03,000\nHello World\n\n2\n00:00:03,500 --> 00:00:06,000\nThis is a test",
    "tts_voice": "BV074_streaming",
    "user_id": "user-123"
  }'
```

Response:
```json
{
  "task_id": "task-uuid",
  "status": "success",
  "audio_id": "uuid-audio-id",
  "audio_base64": "...",
  "duration_ms": 6000,
  "size_bytes": 96000,
  "message": null
}
```

Save the `audio_id` for use in the merge endpoint.

### Step 3: Merge Video with Audio

Use the `/merge-video` endpoint to combine the video and audio:

```bash
curl -X POST http://localhost:8000/merge-video \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "uuid-video-id",
    "audio_id": "uuid-audio-id",
    "volume_level": 0,
    "scale_audio_duration": false
  }'
```

Response:
```json
{
  "video_id": "uuid-merged-video-id",
  "status": "success",
  "file_size": 5242880,
  "output_filename": "input_video_merged.mp4",
  "volume_level": 0,
  "scale_audio_duration": false,
  "message": "Warning: Video duration (10.00s) differs from audio duration (6.00s). Consider using scale_audio_duration=true."
}
```

The merged video is now saved in the database with a new `video_id`.

## API Parameters

### Request Body

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `video_id` | string | Yes | - | Video ID from `/upload-video` endpoint (source video) |
| `audio_id` | string | Yes | - | Audio ID from `/tts/generate` endpoint (audio to merge) |
| `volume_level` | integer | No | 100 | Volume level for video's original audio (0-100). 0 = mute video audio, 100 = preserve original volume |
| `scale_audio_duration` | boolean | No | false | If `true`, scales audio duration to match video duration using time-stretching filter (pitch-preserving). If `false`, allows duration mismatch naturally |

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `video_id` | string | New merged video GUID saved to database |
| `status` | string | Operation status ("success" or "error") |
| `file_size` | integer | File size of merged video in bytes |
| `output_filename` | string | Output filename of merged video |
| `volume_level` | integer | Volume level used for video audio (0-100) |
| `scale_audio_duration` | boolean | Whether audio duration was scaled |
| `message` | string | Additional message or warning (e.g., duration mismatch warning) |

## Use Cases

### 1. Replace Video Audio Completely (Mute Video, Add TTS Audio)

Mute the video's original audio and add TTS audio:

```bash
curl -X POST http://localhost:8000/merge-video \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "video-uuid",
    "audio_id": "audio-uuid",
    "volume_level": 0,
    "scale_audio_duration": false
  }'
```

**Result**: Video's original audio is completely muted, replaced with TTS audio.

### 2. Add TTS Audio While Reducing Video Audio

Lower video audio volume and mix with TTS:

```bash
curl -X POST http://localhost:8000/merge-video \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "video-uuid",
    "audio_id": "audio-uuid",
    "volume_level": 30,
    "scale_audio_duration": false
  }'
```

**Result**: Video's original audio is reduced to 30% volume, then merged with TTS audio.

### 3. Sync Audio Duration with Video (Auto-Scale)

Stretch or compress audio to match video duration:

```bash
curl -X POST http://localhost:8000/merge-video \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "video-uuid",
    "audio_id": "audio-uuid",
    "volume_level": 0,
    "scale_audio_duration": true
  }'
```

**Result**: 
- Video audio is muted
- Audio duration is automatically scaled to match video length (pitch-preserving time-stretch)
- No gaps or cut-offs between video and audio

### 4. Mix Audio with Scaling

Mix reduced video audio with scaled TTS audio:

```bash
curl -X POST http://localhost:8000/merge-video \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "video-uuid",
    "audio_id": "audio-uuid",
    "volume_level": 50,
    "scale_audio_duration": true
  }'
```

**Result**: Video audio reduced to 50%, TTS audio scaled to match video duration, then mixed together.

## Technical Details

### Volume Level Calculation

- **0**: Video audio is completely muted before merge
  - Formula: `volume = 0/100 = 0.0` (no audio from video)
  
- **100**: Video audio is preserved at original volume
  - Formula: `volume = 100/100 = 1.0` (full volume)
  
- **50**: Video audio is reduced to half volume
  - Formula: `volume = 50/100 = 0.5` (half volume)

### Audio Duration Scaling

When `scale_audio_duration=true`, the endpoint uses FFmpeg's `atempo` filter for time-stretching:

- **Calculation**: `tempo_ratio = video_duration / audio_duration`
- **Clamping**: Tempo ratio is clamped to 0.5x - 2.0x for reasonable quality
- **Filter**: Applied as `atempo={tempo_ratio}` before mixing

**Example**:
- Video duration: 10 seconds
- Audio duration: 6 seconds
- Tempo ratio: 10 / 6 = 1.667 (stretch audio by 66.7%)
- Filter applied: `atempo=1.6667`

**Advantages**:
- No pitch change (unlike simple speed adjustment)
- Natural-sounding result
- Preserves audio quality

### Filter Chain Processing

FFmpeg command structure:
```
ffmpeg -i video_input -i audio_input \
  -c:v copy \
  -af "volume=N,atempo=M" \
  -c:a aac -b:a 128k \
  -map 0:v:0 -map 1:a:0 \
  output.mp4
```

- `-c:v copy`: Copy video stream without re-encoding (preserves codec)
- `-af`: Audio filter chain (volume + atempo)
- `-c:a aac`: Encode audio as AAC
- `-map 0:v:0 -map 1:a:0`: Map video from input 1, audio from input 2

## Warnings and Notes

### Duration Mismatch Warning

If video and audio durations differ significantly and `scale_audio_duration=false`, the API returns:

```json
{
  "message": "Warning: Video duration (10.00s) differs from audio duration (6.00s). Consider using scale_audio_duration=true."
}
```

**How FFmpeg handles this**:
- If audio is shorter: Video plays with silence at the end
- If audio is longer: Audio is cut off when video ends
- Use `scale_audio_duration=true` to prevent this

### File Size Considerations

- Merged videos inherit the video codec from the source (no re-encoding)
- Audio is re-encoded as AAC at 128 kbps
- Expected file size ≈ original video size + audio size

### Processing Time

- Time depends on:
  - Video and audio duration
  - Whether `scale_audio_duration=true` (requires audio re-encoding)
  - System hardware (CPU/GPU availability)
  
- Typical times:
  - 1 min video: 5-30 seconds
  - 10 min video: 30-60 seconds

## Error Handling

### 404 Not Found

```json
{
  "detail": "Video with ID xyz not found or has been deleted"
}
```

**Causes**:
- Video ID is invalid or doesn't exist
- Video has been deleted
- Audio ID is invalid or doesn't exist

### 500 Internal Server Error

```json
{
  "detail": "Failed to merge video and audio: [error details]"
}
```

**Common causes**:
- Input video/audio files are corrupted
- Insufficient disk space
- FFmpeg not installed or not in PATH
- Audio/video codec not supported

## Examples

### Python Example

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# Step 1: Upload video
with open("video.mp4", "rb") as f:
    video_response = requests.post(
        f"{BASE_URL}/upload-video",
        files={"file": f}
    )
    video_id = video_response.json()["id"]
    print(f"Uploaded video: {video_id}")

# Step 2: Generate audio
audio_response = requests.post(
    f"{BASE_URL}/tts/generate",
    json={
        "srt_content": "1\n00:00:00,000 --> 00:00:05,000\nHello World",
        "tts_voice": "BV074_streaming",
        "user_id": "user-123"
    }
)
audio_id = audio_response.json()["audio_id"]
print(f"Generated audio: {audio_id}")

# Step 3: Merge video with audio
merge_response = requests.post(
    f"{BASE_URL}/merge-video",
    json={
        "video_id": video_id,
        "audio_id": audio_id,
        "volume_level": 0,  # Mute video audio
        "scale_audio_duration": True  # Scale audio to match video
    }
)
result = merge_response.json()
merged_video_id = result["video_id"]
print(f"Merged video: {merged_video_id}")
print(f"Status: {result['status']}")
print(f"Message: {result.get('message', 'No message')}")
```

### cURL Example with Full Workflow

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"
USER_ID="user-123"

# Upload video
echo "Uploading video..."
VIDEO_RESPONSE=$(curl -s -X POST "$BASE_URL/upload-video" \
  -F "file=@video.mp4" \
  -H "Content-Type: multipart/form-data")
VIDEO_ID=$(echo $VIDEO_RESPONSE | jq -r '.id')
echo "Video ID: $VIDEO_ID"

# Generate audio via TTS
echo "Generating audio..."
AUDIO_RESPONSE=$(curl -s -X POST "$BASE_URL/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "srt_content": "1\n00:00:00,000 --> 00:00:05,000\nHello World",
    "tts_voice": "BV074_streaming",
    "user_id": "'$USER_ID'"
  }')
AUDIO_ID=$(echo $AUDIO_RESPONSE | jq -r '.audio_id')
echo "Audio ID: $AUDIO_ID"

# Merge video with audio
echo "Merging video with audio..."
MERGE_RESPONSE=$(curl -s -X POST "$BASE_URL/merge-video" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "'$VIDEO_ID'",
    "audio_id": "'$AUDIO_ID'",
    "volume_level": 0,
    "scale_audio_duration": true
  }')
MERGED_VIDEO_ID=$(echo $MERGE_RESPONSE | jq -r '.video_id')
echo "Merged Video ID: $MERGED_VIDEO_ID"
echo "Response: $MERGE_RESPONSE" | jq .
```

## Best Practices

1. **Always use `scale_audio_duration=true` when**:
   - Audio and video durations differ significantly
   - You want seamless playback without gaps or cuts

2. **Use `volume_level=0` when**:
   - The video has distracting background audio
   - You want the TTS audio to be the primary audio track

3. **Use `volume_level=30-50` when**:
   - You want to preserve some ambient sound from the video
   - You need both video audio and TTS audio to coexist

4. **Check for warnings**:
   - Always read the `message` field in the response
   - Duration mismatch warnings suggest using `scale_audio_duration=true`

5. **File organization**:
   - Keep track of merged video IDs for later reference
   - Delete old videos to manage quota
   - Use descriptive naming in downstream processing

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Audio file not found" | Audio ID is invalid | Ensure audio was generated successfully via `/tts/generate` |
| "Video file not found" | Video ID is invalid | Ensure video was uploaded successfully via `/upload-video` |
| FFmpeg errors | Missing codecs or libraries | Check FFmpeg installation: `ffmpeg -version` |
| Very long processing time | Large files or slow CPU | For large videos, consider splitting or using GPU acceleration |
| Audio cut off abruptly | Duration mismatch without scaling | Use `scale_audio_duration=true` |
| No video audio output | `volume_level` is 0 | If you need video audio, increase `volume_level` above 0 |

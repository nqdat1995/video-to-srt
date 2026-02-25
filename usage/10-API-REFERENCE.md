# API Reference (Tham chiếu API)

## Base URL

```
http://localhost:8000
```

## Health Check

```bash
GET /health
```

## Response Format

All responses include:
- `status`: `success`, `processing`, `completed`, `failed`
- `data` or `result`: Response data
- `error`: Error message if failed

## Extract SRT Endpoints

### Synchronous Extraction

```bash
POST /extract-srt
Content-Type: application/json
```

**Request Body** (Choose one of the following):

**Option 1: Using `video_id` (from /upload-video endpoint)**
```json
{
  "video_id": "a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6",
  "lang": "vi",
  "device": "cpu",
  "target_fps": 4.0,
  "conf_min": 0.5
}
```

**Option 2: Using `video` (local file path)**
```json
{
  "video": "uploads/sample.mp4",
  "lang": "vi",
  "device": "cpu",
  "target_fps": 4.0,
  "conf_min": 0.5
}
```

**Note on Priority:**
- If both `video_id` and `video` are provided, `video_id` takes priority
- If `video_id` is provided, the system will:
  1. Query the database to fetch the video file path
  2. Return error 404 if video not found
  3. Automatically save the extracted SRT to the configured `SRT_OUTPUT_DIR` directory
  4. Include `srt_output_path` in the response
- If only `video` is provided, SRT is returned in response only (no auto-save)

**Response**: `ExtractResponse` with optional `srt_output_path`

### Full-FPS Extraction

```bash
POST /extract-srt-frames
Content-Type: application/json
```

**Request Body** (same options as `/extract-srt`):

**Option 1: Using `video_id`**
```json
{
  "video_id": "a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6",
  "lang": "vi",
  "target_fps": 4.0
}
```

**Option 2: Using `video`**
```json
{
  "video": "uploads/sample.mp4",
  "lang": "vi",
  "target_fps": 4.0
}
```

**Response**: `ExtractResponse` with optional `srt_output_path`

### Asynchronous Extraction

```bash
POST /extract-srt-async
Content-Type: application/json

{
  "video": "uploads/long_video.mp4",
  "lang": "vi"
}
```

**Response**: `{"task_id": "uuid", "status": "processing"}`

## Task Management Endpoints

### Get Task Status

```bash
GET /task/{task_id}
```

**Response**: `TaskStatusResponse`

### Cancel Task

```bash
DELETE /task/{task_id}
```

## Video Processing Endpoints

### Blur Original Subtitles

```bash
POST /blur
Content-Type: application/json
```

**Request Body** (Choose one of the following):

**Option 1: Using `video_id` (from /upload-video endpoint)**
```json
{
  "video_id": "a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6",
  "srt_detail": [
    {
      "x1": 100,
      "y1": 950,
      "x2": 1820,
      "y2": 1050,
      "srt_time": "00:00:01,000 --> 00:00:05,000"
    }
  ],
  "blur_strength": 25,
  "output_suffix": "blurred",
  "use_gpu": true
}
```

**Option 2: Using `video_path` (local file path - backward compatible)**
```json
{
  "video_path": "uploads/video.mp4",
  "srt_detail": [
    {
      "x1": 100,
      "y1": 950,
      "x2": 1820,
      "y2": 1050,
      "srt_time": "00:00:01,000 --> 00:00:05,000"
    }
  ],
  "blur_strength": 25,
  "output_suffix": "blurred",
  "use_gpu": true
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "output_path": "uploads/video_blurred.mp4",
    "video_path": "uploads/video.mp4",
    "blur_strength": 25,
    "srt_count": 1,
    "gpu_acceleration": true,
    "message": "Video blurred successfully"
  }
}
```

### Add Subtitles to Video

```bash
POST /subtitle
Content-Type: application/json
```

**Request Body** (Choose one of the following):

**Option 1: Using `video_id` with `srt_content` (NEW - Recommended)**
```json
{
  "video_id": "a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6",
  "srt_content": "1\n00:00:01,000 --> 00:00:05,000\nSubtitle 1\n\n2\n00:00:06,000 --> 00:00:10,000\nSubtitle 2",
  "output_suffix": "subtitled",
  "use_gpu": true
}
```

**Option 2: Using `video_path` with `srt_content` (Backward compatible - recommended over srt_path)**
```json
{
  "video_path": "uploads/video.mp4",
  "srt_content": "1\n00:00:01,000 --> 00:00:05,000\nSubtitle 1\n\n2\n00:00:06,000 --> 00:00:10,000\nSubtitle 2",
  "output_suffix": "subtitled",
  "use_gpu": true
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "output_path": "uploads/video_subtitled.mp4",
    "video_path": "uploads/video.mp4",
    "srt_path": "srt_temp/srt_a1b2c3d4-e5f6.srt",
    "gpu_acceleration": true,
    "message": "Video processed successfully"
  }
}
```

### Blur and Add Subtitles

```bash
POST /blur-and-subtitle
Content-Type: application/json
```

**Request Body** (Choose one of the following):

**Option 1: Using `video_id` with `srt_content` (NEW - Recommended)**
```json
{
  "video_id": "a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6",
  "srt_content": "1\n00:00:01,000 --> 00:00:05,000\nSubtitle 1\n\n2\n00:00:06,000 --> 00:00:10,000\nSubtitle 2",
  "srt_detail": [
    {
      "x1": 100,
      "y1": 950,
      "x2": 1820,
      "y2": 1050,
      "srt_time": "00:00:01,000 --> 00:00:05,000"
    }
  ],
  "blur_strength": 25,
  "output_suffix": "vnsrt",
  "use_gpu": true
}
```

**Option 2: Using `video_path` with `srt_content` (Backward compatible)**
```json
{
  "video_path": "uploads/video.mp4",
  "srt_content": "1\n00:00:01,000 --> 00:00:05,000\nSubtitle 1\n\n2\n00:00:06,000 --> 00:00:10,000\nSubtitle 2",
  "srt_detail": [
    {
      "x1": 100,
      "y1": 950,
      "x2": 1820,
      "y2": 1050,
      "srt_time": "00:00:01,000 --> 00:00:05,000"
    }
  ],
  "blur_strength": 25,
  "output_suffix": "vnsrt",
  "use_gpu": true
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "output_path": "uploads/video_vnsrt.mp4",
    "video_path": "uploads/video.mp4",
    "srt_path": "srt_temp/srt_a1b2c3d4-e5f6.srt",
    "blur_strength": 25,
    "srt_count": 2,
    "gpu_acceleration": true,
    "message": "Video processed successfully"
  }
}
```

## TTS Endpoints

### Generate Audio from SRT

```bash
POST /tts/generate
Content-Type: application/json

{
  "srt_content": "1\n00:00:01,000 --> 00:00:05,000\nText\n",
  "tts_voice": "BV074_streaming",
  "output_filename": "output.wav",
  "return_base64": true
}
```

**Response**: `TTSResponse`

## Video Upload Endpoints

### Upload Video

```bash
POST /upload-video
Content-Type: multipart/form-data

file: <video file>
user_id: user-123 (optional)
```

**Response**: `VideoUploadResponse`

### Get User Quota

```bash
GET /user/{user_id}/quota
```

**Response**: `UserQuotaResponse`

### List User's Videos

```bash
GET /user/{user_id}/videos?include_deleted=false
```

**Response**:
```json
{
  "user_id": "string",
  "total_count": 10,
  "videos": [...]
}
```

### Delete Video

```bash
DELETE /video/{video_id}?user_id=user_id
```

**Response**: `{"status": "success", "message": "..."}`

## Response Models

### ExtractResponse

```json
{
  "srt": "string",
  "srt_detail": [
    {
      "srt": "string",
      "srt_time": "HH:MM:SS,mmm --> HH:MM:SS,mmm",
      "x1": float,
      "y1": float,
      "x2": float,
      "y2": float
    }
  ],
  "stats": {
    "mode": "ocr|stream",
    "frames_seen": int,
    "frames_sampled": int,
    "frames_hashed_skipped": int,
    "frames_ocr": int,
    "cues": int,
    "timing_ms": {
      "total": float,
      "decode": float,
      "ocr": float
    },
    "video": {
      "width": int,
      "height": int,
      "src_fps": float
    }
  },
  "srt_output_path": "string|null"
}
```

**Field Descriptions:**
- `srt`: Complete SRT subtitle text
- `srt_detail`: Array of detailed subtitle information with bounding box coordinates
- `stats`: Processing statistics
- `srt_output_path`: (NEW) Path where SRT file was saved on server (only when using `video_id`)

### TaskStatusResponse

```json
{
  "task_id": "string",
  "status": "processing|completed|failed",
  "progress": 0.0-1.0,
  "result": "ExtractResponse|null",
  "error": "string|null"
}
```

### TTSResponse

```json
{
  "task_id": "string",
  "status": "success|failed",
  "audio_filename": "string",
  "audio_path": "string",
  "audio_base64": "string|null",
  "duration_ms": float,
  "size_bytes": int,
  "message": "string|null"
}
```

### VideoUploadResponse

```json
{
  "id": "uuid",
  "user_id": "string",
  "filename": "string",
  "file_size": int,
  "created_at": "ISO8601",
  "status": "success",
  "message": "string"
}
```

### UserQuotaResponse

```json
{
  "user_id": "string",
  "video_count": int,
  "max_videos": int,
  "remaining_quota": int,
  "total_size_bytes": int,
  "last_updated": "ISO8601"
}
```

## Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid parameters |
| 404 | Not Found | Task/file/resource not found |
| 413 | Payload Too Large | File exceeds MAX_UPLOAD_SIZE_MB |
| 503 | Service Unavailable | TTS disabled or service down |
| 500 | Server Error | Processing failed |

## Error Response Format

```json
{
  "detail": "Error message here"
}
```

## Interactive Documentation

Full interactive documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Rate Limiting

Currently no rate limiting. Implement as needed based on your requirements.

## Authentication

Currently no authentication. All endpoints are public. Consider adding:
- API key authentication
- JWT tokens
- OAuth 2.0

## CORS

CORS enabled for all origins. Configure in `app/main.py` as needed:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Versioning

API version follows application version in `app/core/config.py`.

Current version: Available at `/docs` page.

## Request/Response Examples

See detailed examples in:
- [04-EXTRACT-SRT.md](04-EXTRACT-SRT.md)
- [06-VIDEO-PROCESSING.md](06-VIDEO-PROCESSING.md)
- [07-TTS-SYNTHESIS.md](07-TTS-SYNTHESIS.md)
- [08-VIDEO-UPLOAD.md](08-VIDEO-UPLOAD.md)

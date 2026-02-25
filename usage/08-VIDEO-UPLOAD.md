# Video Upload with Quota Management (Tải lên video)

## Quick Start

### Upload Video (Generate User ID)

```bash
curl -X POST "http://localhost:8000/upload-video" \
  -F "file=@/path/to/video.mp4"
```

### Upload with Specific User ID

```bash
curl -X POST "http://localhost:8000/upload-video" \
  -F "file=@/path/to/video.mp4" \
  -F "user_id=user-123"

# Response:
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "user_id": "user-123",
#   "filename": "video.mp4",
#   "file_size": 1048576,
#   "created_at": "2026-02-25T10:30:45.123456",
#   "status": "success",
#   "message": "Video uploaded successfully"
# }
```

## Python Client - Single Upload

```python
import requests
from pathlib import Path

video_file = Path("video.mp4")
with open(video_file, "rb") as f:
    response = requests.post(
        "http://localhost:8000/upload-video",
        files={"file": f},
        data={"user_id": "user-123"}
    )

if response.status_code == 200:
    result = response.json()
    video_id = result["id"]
    print(f"✓ Video uploaded: {video_id}")
    print(f"  File size: {result['file_size']} bytes")
    print(f"  Uploaded at: {result['created_at']}")
else:
    print(f"✗ Upload failed: {response.status_code}")
    print(response.text)
```

## Python Client - Batch Upload

```python
import requests
from pathlib import Path

video_dir = Path("videos")
user_id = "batch-user-001"
video_ids = []

for video_file in video_dir.glob("*.mp4"):
    with open(video_file, "rb") as f:
        response = requests.post(
            "http://localhost:8000/upload-video",
            files={"file": f},
            data={"user_id": user_id}
        )
    
    if response.status_code == 200:
        video_id = response.json()["id"]
        video_ids.append(video_id)
        print(f"✓ Uploaded: {video_file.name}")
    else:
        print(f"✗ Failed: {video_file.name}")

print(f"\nTotal uploaded: {len(video_ids)}")
```

## Get User Quota Information

### cURL

```bash
curl -X GET "http://localhost:8000/user/user-123/quota"

# Response:
# {
#   "user_id": "user-123",
#   "video_count": 7,
#   "max_videos": 10,
#   "remaining_quota": 3,
#   "total_size_bytes": 5242880000,
#   "last_updated": "2026-02-25T10:30:45.123456"
# }
```

### Python Client

```python
import requests

user_id = "user-123"
response = requests.get(f"http://localhost:8000/user/{user_id}/quota")

if response.status_code == 200:
    quota = response.json()
    print(f"User: {quota['user_id']}")
    print(f"Videos: {quota['video_count']}/{quota['max_videos']}")
    print(f"Remaining: {quota['remaining_quota']}")
    print(f"Total size: {quota['total_size_bytes'] / (1024**3):.2f} GB")
else:
    print(f"Error: {response.status_code}")
```

## List User's Videos

### cURL - Active Videos Only

```bash
curl -X GET "http://localhost:8000/user/user-123/videos"
```

### cURL - Include Deleted Videos

```bash
curl -X GET "http://localhost:8000/user/user-123/videos?include_deleted=true"

# Response:
# {
#   "user_id": "user-123",
#   "total_count": 7,
#   "videos": [
#     {
#       "id": "550e8400-e29b-41d4-a716-446655440000",
#       "filename": "video.mp4",
#       "file_size": 1048576,
#       "created_at": "2026-02-25T10:30:45.123456",
#       "is_deleted": false,
#       "deleted_at": null
#     },
#     ...
#   ]
# }
```

### Python Client

```python
import requests

user_id = "user-123"
response = requests.get(
    f"http://localhost:8000/user/{user_id}/videos",
    params={"include_deleted": False}
)

if response.status_code == 200:
    data = response.json()
    print(f"Total videos: {data['total_count']}")
    for video in data['videos']:
        print(f"  - {video['filename']} ({video['file_size']} bytes)")
        print(f"    ID: {video['id']}")
        print(f"    Uploaded: {video['created_at']}")
```

## Delete Video

### cURL

```bash
curl -X DELETE "http://localhost:8000/video/550e8400-e29b-41d4-a716-446655440000?user_id=user-123"

# Response:
# {
#   "status": "success",
#   "message": "Video deleted successfully"
# }
```

### Python Client

```python
import requests

video_id = "550e8400-e29b-41d4-a716-446655440000"
user_id = "user-123"

response = requests.delete(
    f"http://localhost:8000/video/{video_id}",
    params={"user_id": user_id}
)

if response.status_code == 200:
    print(f"✓ Video deleted successfully")
else:
    print(f"✗ Delete failed: {response.status_code}")
```

## Complete Upload + Extraction Workflow

```python
import requests
from pathlib import Path

user_id = "workflow-demo"
video_file = Path("input.mp4")

# Step 1: Upload video
print("Step 1: Uploading video...")
with open(video_file, "rb") as f:
    upload_resp = requests.post(
        "http://localhost:8000/upload-video",
        files={"file": f},
        data={"user_id": user_id}
    )

video_id = upload_resp.json()["id"]
print(f"✓ Video uploaded: {video_id}")

# Step 2: Check quota
print("\nStep 2: Checking quota...")
quota_resp = requests.get(f"http://localhost:8000/user/{user_id}/quota")
quota = quota_resp.json()
print(f"  Remaining quota: {quota['remaining_quota']}/{quota['max_videos']}")

# Step 3: Get file path
local_video_path = f"./uploads/{video_id}.mp4"

# Step 4: Extract subtitles
print("\nStep 3: Extracting subtitles...")
extract_resp = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": local_video_path,
        "lang": "vi",
        "target_fps": 4.0
    }
)

srt_content = extract_resp.json()["srt"]
print(f"✓ Extracted {len(srt_content.splitlines()) // 4} subtitle cues")

# Step 5: Generate audio
print("\nStep 4: Synthesizing audio...")
tts_resp = requests.post(
    "http://localhost:8000/tts/generate",
    json={
        "srt_content": srt_content,
        "tts_voice": "BV074_streaming",
        "output_filename": f"{video_id}_audio.wav"
    }
)

audio_path = tts_resp.json()["audio_path"]
print(f"✓ Audio synthesized: {audio_path}")

print(f"\n✓ Workflow complete!")
print(f"  Video ID: {video_id}")
print(f"  Subtitles: Ready")
print(f"  Audio: {audio_path}")
```

## Upload Configuration

Configure upload behavior in `.env`:

```bash
# Database connection
DATABASE_URL=postgresql://video_user:video_password@localhost:5432/video_srt_db

# Upload settings
UPLOAD_DIR=./uploads                # Directory for uploaded files
MAX_VIDEOS_PER_USER=10              # Max videos per user before auto-cleanup
MAX_UPLOAD_SIZE_MB=500              # Max file size in MB

# Server settings
HOST=0.0.0.0
PORT=8000
```

## Upload Limits

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `MAX_VIDEOS_PER_USER` | 10 | 1-100 | Videos per user before auto-cleanup |
| `MAX_UPLOAD_SIZE_MB` | 500 | 1-10000 | Max file size in MB |
| Allowed formats | mp4, avi, mov, mkv, flv, wmv, webm | - | Supported video formats |

## Auto-cleanup Behavior

When user uploads 11th video (exceeds `MAX_VIDEOS_PER_USER=10`):

1. Oldest video (1st uploaded) is automatically deleted
2. Video file removed from disk
3. Video marked as `is_deleted=true` in database
4. User quota counter updates automatically
5. User quota information reflects the change

Example:
```
Step 1: User uploads 10 videos → quota: 10/10
Step 2: User uploads video #11 → oldest auto-deleted → quota: 10/10
Step 3: Get quota → remaining_quota: 0
Step 4: User deletes 1 video manually → quota: 9/10 → remaining_quota: 1
```

## Database Schema

Videos stored in PostgreSQL with:
- `id` (GUID): Unique video identifier
- `user_id`: User who uploaded
- `filename`: Original filename
- `file_path`: Storage location
- `file_size`: File size in bytes
- `created_at`: Upload timestamp
- `is_deleted`: Soft delete flag
- `deleted_at`: Deletion timestamp

## Response Models

### Upload Response

```json
{
  "id": "uuid",
  "user_id": "string",
  "filename": "string",
  "file_size": 1048576,
  "created_at": "2026-02-25T10:30:45.123456",
  "status": "success",
  "message": "string"
}
```

### Quota Response

```json
{
  "user_id": "string",
  "video_count": 7,
  "max_videos": 10,
  "remaining_quota": 3,
  "total_size_bytes": 5242880000,
  "last_updated": "2026-02-25T10:30:45.123456"
}
```

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| File too large | Exceeds MAX_UPLOAD_SIZE_MB | Upload smaller file |
| Invalid format | Not in ALLOWED_VIDEO_FORMATS | Use mp4, avi, mov, mkv |
| User quota exceeded | Already at MAX_VIDEOS_PER_USER | Delete older videos first |
| Database error | PostgreSQL not running | Start Docker containers |
| Permission denied | Can't write to UPLOAD_DIR | Check directory permissions |

See [09-TROUBLESHOOTING.md](09-TROUBLESHOOTING.md) for more solutions.

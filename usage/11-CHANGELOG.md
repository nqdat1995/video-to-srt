# Changelog - Video ID Support for SRT Extraction

## Version Update - SRT Extraction API Enhancement

### Date: February 25, 2026

### Summary

Enhanced `/extract-srt` and `/extract-srt-frames` endpoints to support extracting SRT files using `video_id` from the database instead of requiring `output_path`. This enables better integration with the `/upload-video` endpoint and provides automatic SRT file management.

### Key Changes

#### 1. **Request Model Changes** (`app/models/requests.py`)

- **Removed**: `output_path` field (no longer needed)
- **Added**: `video_id` field (optional, from /upload-video endpoint)

**Migration Guide:**
- **Old Usage**: Send `video` path + `output_path` → System returns SRT in response only
- **New Usage**: Send `video_id` → System fetches video path from DB + auto-saves SRT

#### 2. **Response Model Changes** (`app/models/responses.py`)

- **Added**: `srt_output_path` field in `ExtractResponse`
  - Contains the file path where SRT was saved (only when using `video_id`)
  - `null` when using direct `video` path

#### 3. **Configuration Changes** (`app/core/config.py`)

- **Added**: New environment variable `SRT_OUTPUT_DIR`
  - Default: `./srt_output`
  - Configurable via environment variable
  - Automatically creates directory if it doesn't exist

#### 4. **Route Handler Changes** (`app/api/routes.py`)

- **Updated**: Both `/extract-srt` and `/extract-srt-frames` endpoints
- Now accept database session via dependency injection
- Query video metadata from database when `video_id` is provided
- Return 404 error if video not found or marked as deleted
- Pass metadata to processor for auto-save functionality

#### 5. **Video Processor Changes** (`app/services/video_processor.py`)

**New Parameters Added to All Processing Methods:**
- `video_path`: Optional override for video file path
- `original_filename`: Original filename for SRT naming
- `auto_save_srt`: Flag to enable auto-save functionality

**Updated Methods:**
- `process_video()`: Added new parameters for database video support
- `process_video_fullfps()`: Added new parameters for database video support
- `_extract_from_stream()`: Supports auto-save with proper path handling
- `_extract_with_ocr()`: Passes parameters to frame processor
- `_process_video_frames()`: Implements auto-save logic with proper directory creation

**Auto-Save Logic:**
- When `auto_save_srt=True` and `original_filename` provided:
  - Creates `SRT_OUTPUT_DIR` if needed
  - Strips extension from original filename
  - Saves SRT as: `{SRT_OUTPUT_DIR}/{filename_without_ext}.srt`
  - Returns path in `srt_output_path` field
- When using direct `video` path:
  - No auto-save (returns `srt_output_path=null`)
  - SRT content available in response `srt` field

### API Usage Examples

#### Using `video_id` (Recommended for Database Videos)

```bash
curl -X POST "http://localhost:8000/extract-srt" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6",
    "lang": "vi",
    "target_fps": 4.0
  }'
```

**Response:**
```json
{
  "srt": "1\n00:00:01,000 --> 00:00:05,000\nText\n\n...",
  "srt_output_path": "./srt_output/video_filename.srt",
  "srt_detail": [...],
  "stats": {...}
}
```

#### Using `video` (Direct File Path)

```bash
curl -X POST "http://localhost:8000/extract-srt" \
  -H "Content-Type: application/json" \
  -d '{
    "video": "uploads/sample.mp4",
    "lang": "vi",
    "target_fps": 4.0
  }'
```

**Response:**
```json
{
  "srt": "1\n00:00:01,000 --> 00:00:05,000\nText\n\n...",
  "srt_output_path": null,
  "srt_detail": [...],
  "stats": {...}
}
```

### Priority Logic

When processing extraction requests:

1. **If `video_id` provided**: Fetch from database, auto-save SRT (overrides `video` parameter)
2. **Else if `video` provided**: Use direct file path, no auto-save
3. **Else**: Return 400 error (either `video_id` or `video` must be provided)

### Error Handling

- **404 Error**: Video with given `video_id` not found in database
- **404 Error**: Video marked as deleted (`is_deleted=True`)
- **400 Error**: Neither `video_id` nor `video` provided
- **500 Error**: Unable to create SRT output directory

### Database Integration

The updated endpoints now require PostgreSQL database access:

- **Query**: `videos` table by `id` and `is_deleted` status
- **Fields Used**: `filename`, `file_path`
- **ORM Model**: `Video` model from `app/models/database.py`

### File Naming Convention

When auto-saving with `video_id`:

- **Original Uploaded File**: `a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6.mp4`
- **Stored Filename**: `example_video.mp4` (in database)
- **Generated SRT File**: `example_video.srt` (in SRT_OUTPUT_DIR)

### Environment Configuration

Update your `.env` file:

```bash
# New setting
SRT_OUTPUT_DIR=./srt_output

# Existing settings (unchanged)
DATABASE_URL=postgresql://video_user:video_password@localhost:5432/video_srt_db
UPLOAD_DIR=./uploads
```

### Backward Compatibility

- Old requests using direct `video` path continue to work
- `output_path` field removed (no longer supported)
- Both old and new usage patterns return valid responses

### Testing Checklist

- [x] `/extract-srt` with `video_id` creates SRT file in configured directory
- [x] `/extract-srt-frames` with `video_id` creates SRT file in configured directory
- [x] `/extract-srt` with `video` path returns SRT in response without auto-save
- [x] `/extract-srt-frames` with `video` path returns SRT in response without auto-save
- [x] 404 returned when `video_id` not found in database
- [x] 400 returned when neither `video_id` nor `video` provided
- [x] SRT output directory created automatically
- [x] Response includes `srt_output_path` when auto-saved
- [x] Response includes `srt_output_path=null` when not auto-saved

### Documentation Updates

Updated documentation files:
- `usage/04-EXTRACT-SRT.md`: New examples with `video_id` usage
- `usage/09-CONFIGURATION.md`: New `SRT_OUTPUT_DIR` configuration option
- `usage/10-API-REFERENCE.md`: Updated request/response model documentation


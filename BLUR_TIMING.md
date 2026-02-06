# Blur Video Implementation - Timing Control

## Current Issue Fix

### Problem
Previously, blur was applied to the entire video duration instead of only during the specific time ranges where subtitles appear (based on `srt_time`).

### Solution
Implemented time-aware blur using FFmpeg's `enable` filter with `between(t,start,end)` expression.

## How It Works

### 1. **SRT Detail Structure**
The `/extract-srt` API returns:
```json
{
  "srt": "Subtitle text",
  "srt_time": "00:00:01,500 --> 00:00:05,000",  // Time when blur is active
  "x1": 100.0,
  "y1": 50.0,
  "x2": 500.0,
  "y2": 150.0
}
```

### 2. **Time Parsing**
- Format: `HH:MM:SS,mmm --> HH:MM:SS,mmm`
- Converts to seconds: `1.5 --> 5.0`
- Used in FFmpeg's `between(t,start,end)` condition

### 3. **FFmpeg Filter Chain**
For each srt_detail item, the following filter sequence is applied:

```
[0:v]format=yuva420p[base]                              # Start with video
[base]split=2[base0][crop0]                            # Split into 2 streams
[crop0]crop=w=400:h=100:x=100:y=50[cropped0]          # Crop the blur region
[cropped0]boxblur=luma_radius=10:chroma_radius=10[blurred0]  # Apply blur
[blurred0]pad=w=1920:h=1080:x=100:y=50:color=black@0[padded0]  # Pad back to original size
[base0][padded0]overlay=x=0:y=0:enable='between(t,1.5,5.0)'[blurred_overlay0]  # Overlay ONLY during time window
```

### 4. **Key Components**

#### Split Filter
Duplicates the video stream so we can process one copy for blur and keep original as base.

#### Crop Filter  
Extracts only the region defined by (x1,y1) to (x2,y2) coordinates.

#### Boxblur Filter
Applies Gaussian blur with strength controlled by luma_radius and chroma_radius.

#### Pad Filter
Restores the cropped region to its original position in full video frame, with black padding outside.

#### Overlay Filter with Enable
Critical part - overlays the blurred region **only during the specified time window**:
```
enable='between(t,start_time,end_time)'
```
- `t` = current frame time in seconds
- `between(t,1.5,5.0)` = true only when 1.5 ≤ t ≤ 5.0
- Outside this window, original unblurred video is shown

### 5. **Multiple Blur Regions**
If there are multiple subtitles to blur, the chain is chained together:
```
Stream 1: [base] → [base0][crop0] → blur[0] → overlay[0] → [blurred_overlay0]
Stream 2: [blurred_overlay0] → [base1][crop1] → blur[1] → overlay[1] → [blurred_overlay1]
...
Final: [blurred_overlay_N] → add subtitles
```

## API Usage Example

### Step 1: Extract SRT with Coordinates
```bash
curl -X POST http://localhost:8000/extract-srt \
  -H "Content-Type: application/json" \
  -d {
    "video_path": "input.mp4",
    "use_gpu": true
  }
```

Response:
```json
{
  "srt": "Full SRT text...",
  "srt_detail": [
    {
      "srt": "Hello world",
      "srt_time": "00:00:01,500 --> 00:00:05,000",
      "x1": 100, "y1": 50, "x2": 500, "y2": 150
    }
  ]
}
```

### Step 2: Blur Video Using SRT Details
```bash
curl -X POST http://localhost:8000/blur \
  -H "Content-Type: application/json" \
  -d {
    "video_path": "input.mp4",
    "srt_detail": [ ... ],  # from step 1
    "blur_strength": 25,
    "use_gpu": true
  }
```

The blur will now be applied **only during the time windows** specified in each srt_detail's srt_time field.

## Performance Considerations

### GPU Acceleration
- AMD AMF (h264_amf): Fast hardware encoding
- NVIDIA NVENC (h264_nvenc): Fast hardware encoding  
- Fallback: libx264 software encoding

### Limitations
- Maximum 3 blur regions per filter chain (for FFmpeg stability)
- Blur radius: 1-13 (higher values = more processing)
- Time precision: ±1 frame at frame boundaries

## Testing

Run the provided test to verify filter chain generation:
```bash
python test_blur_logic.py
```

This will show:
1. Time parsing results
2. Generated FFmpeg filter chain
3. Filter chain breakdown (12+ filter operations)

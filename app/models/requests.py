"""Request models for API endpoints"""

from typing import Optional
from pydantic import BaseModel, Field

from ..core.config import settings


class ExtractRequest(BaseModel):
   """Request model for subtitle extraction"""

   video: str = Field(..., description="Local path to video on server")

   # Sampling / ROI
   target_fps: float = Field(settings.DEFAULT_TARGET_FPS, gt=0.1, le=30.0)
   bottom_start: float = Field(0.55, gt=0.0, lt=1.0)
   max_width: int = Field(1280, ge=320, le=3840)
   enhance: bool = Field(True, description="Apply mild CLAHE to ROI before OCR")

   # OCR config
   lang: str = Field("vi", description="Language code (auto-selects PP-OCRv5 models)")
   device: str = Field("cpu", description='Device: "cpu" or "gpu:0", "gpu:1", etc.')
   det_model: str = Field(
       "PP-OCRv5_mobile_det",
       description="Detection model (kept for compatibility, uses lang-based model in 3.x)"
   )
   rec_model: str = Field(
       "PP-OCRv5_mobile_rec",
       description="Recognition model (kept for compatibility, uses lang-based model in 3.x)"
   )
   use_textline_orientation: bool = Field(
       False,
       description="Enable angle classification for rotated text"
   )
   conf_min: float = Field(0.5, ge=0.0, le=1.0)

   # Hash gating
   hash_dist_thr: int = Field(6, ge=0, le=64)

   # Debounce / fuzzy
   debounce_frames: int = Field(2, ge=1, le=10)
   empty_debounce_frames: int = Field(2, ge=1, le=10)
   sim_thr: float = Field(0.90, ge=0.5, le=1.0)

   # SRT cleanup
   min_duration_ms: int = Field(400, ge=0, le=5000)
   merge_gap_ms: int = Field(250, ge=0, le=3000)

   # Optional fast path
   prefer_subtitle_stream: bool = Field(
       False, 
       description="If subtitle stream exists, extract via ffmpeg instead of OCR"
   )
   output_path: Optional[str] = Field(
       None, 
       description="If set, write .srt to this path on server"
   )


class BlurRequest(BaseModel):
   """Request model for blurring original subtitles in video"""

   video_path: str = Field(..., description="Path to video file on server")
   srt_detail: list = Field(..., description="List of SRT detail objects with coordinates (x1, y1, x2, y2)")
   blur_strength: int = Field(25, ge=1, le=100, description="Blur strength (higher = more blur)")
   output_suffix: str = Field("blurred", description="Output file suffix")
   use_gpu: bool = Field(True, description="Enable GPU acceleration if available")


class SubtitleRequest(BaseModel):
   """Request model for adding SRT subtitles to video"""

   video_path: str = Field(..., description="Path to video file on server")
   srt_path: str = Field(..., description="Path to extracted SRT file")
   output_suffix: str = Field("subtitled", description="Output file suffix")
   use_gpu: bool = Field(True, description="Enable GPU acceleration if available")


class BlurAndSubtitleRequest(BaseModel):
   """Request model for blurring original subtitles and adding new SRT (combined operation)"""

   video_path: str = Field(..., description="Path to video file on server")
   srt_path: str = Field(..., description="Path to extracted SRT file")
   srt_detail: list = Field(..., description="List of SRT detail objects with coordinates (x1, y1, x2, y2)")
   blur_strength: int = Field(25, ge=1, le=100, description="Blur strength (higher = more blur)")
   output_suffix: str = Field("vnsrt", description="Output file suffix")
   use_gpu: bool = Field(True, description="Enable GPU acceleration if available")

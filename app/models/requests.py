"""Request models for API endpoints"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator

from ..core.config import settings


class ExtractRequest(BaseModel):
   """Request model for subtitle extraction"""

   video: Optional[str] = Field(None, description="Local path to video on server (use either this or video_id)")

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
   content_change_thr: float = Field(0.12, ge=0.0, le=1.0, description="Threshold for detecting text content changes (0.0-1.0)")
   text_motion_thr: float = Field(0.08, ge=0.0, le=1.0, description="Threshold for detecting text motion/transitions (0.0-1.0)")
   text_presence_thr: float = Field(0.30, ge=0.0, le=1.0, description="Threshold for detecting text presence changes (0.0-1.0)")
   intensity_spike_thr: float = Field(0.25, ge=0.0, le=1.0, description="Threshold for detecting intensity spikes (0.0-1.0)")

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
   video_id: Optional[str] = Field(
       None,
       description="Video ID from /upload-video endpoint. If provided, system will fetch video path from database and auto-save SRT to configured output directory"
   )

   @field_validator('video', 'video_id', mode='before')
   @classmethod
   def validate_video_source(cls, v):
       """Ensure validator passes through values as-is"""
       return v


class BlurRequest(BaseModel):
   """Request model for blurring original subtitles in video"""

   video_path: Optional[str] = Field(None, description="Path to video file on server (use either this or video_id)")
   video_id: Optional[str] = Field(None, description="Video ID from /upload-video endpoint")
   srt_detail: list = Field(..., description="List of SRT detail objects with coordinates (x1, y1, x2, y2)")
   blur_strength: int = Field(25, ge=1, le=100, description="Blur strength (higher = more blur)")
   blur_expansion_percent: int = Field(0, ge=0, le=10, description="Blur region expansion percentage (0-10%)")
   output_suffix: str = Field("blurred", description="Output file suffix")
   use_gpu: bool = Field(True, description="Enable GPU acceleration if available")


class SubtitleRequest(BaseModel):
   """Request model for adding SRT subtitles to video"""

   video_path: Optional[str] = Field(None, description="Path to video file on server (use either this or video_id)")
   video_id: Optional[str] = Field(None, description="Video ID from /upload-video endpoint")
   srt_content: str = Field(..., description="SRT subtitle content")
   srt_path: Optional[str] = Field(None, description="Internal: Path to SRT file (auto-generated from srt_content)")
   output_suffix: str = Field("subtitled", description="Output file suffix")
   use_gpu: bool = Field(True, description="Enable GPU acceleration if available")
   fontname: str = Field("Arial", description="Subtitle font name")
   fontsize: int = Field(10, ge=1, le=100, description="Subtitle font size in points")
   subtitle_y_position: int = Field(90, ge=0, le=100, description="Vertical position of subtitle as percentage (0=top, 100=bottom)")


class BlurAndSubtitleRequest(BaseModel):
   """Request model for blurring original subtitles and adding new SRT (combined operation)"""

   video_path: Optional[str] = Field(None, description="Path to video file on server (use either this or video_id)")
   video_id: Optional[str] = Field(None, description="Video ID from /upload-video endpoint")
   srt_content: str = Field(..., description="SRT subtitle content")
   srt_path: Optional[str] = Field(None, description="Internal: Path to SRT file (auto-generated from srt_content)")
   srt_detail: list = Field(..., description="List of SRT detail objects with coordinates (x1, y1, x2, y2)")
   blur_strength: int = Field(25, ge=1, le=100, description="Blur strength (higher = more blur)")
   blur_expansion_percent: int = Field(0, ge=0, le=10, description="Blur region expansion percentage (0-10%)")
   output_suffix: str = Field("vnsrt", description="Output file suffix")
   use_gpu: bool = Field(True, description="Enable GPU acceleration if available")
   fontname: str = Field("Arial", description="Subtitle font name")
   fontsize: int = Field(10, ge=1, le=100, description="Subtitle font size in points")
   subtitle_y_position: int = Field(90, ge=0, le=100, description="Vertical position of subtitle as percentage (0=top, 100=bottom")


class MergeVideoRequest(BaseModel):
   """Request model for merging video with audio"""

   video_id: str = Field(..., description="Video ID from /upload-video endpoint (source video)")
   audio_id: str = Field(..., description="Audio ID from /tts/generate endpoint (audio to merge)")
   volume_level: int = Field(100, ge=0, le=100, description="Volume level for video audio before merge (0=mute, 100=preserve)")
   scale_audio_duration: bool = Field(False, description="Scale audio duration to match video duration using atempo filter")


class TTSGenerateRequest(BaseModel):
   """Request model for TTS audio synthesis from SRT"""

   srt_content: str = Field(..., description="SRT subtitle content")
   tts_voice: str = Field("BV074_streaming", description="Voice identifier for TTS synthesis")
   user_id: Optional[str] = Field(None, description="User identifier (if not provided, defaults to 'anonymous')")
   return_base64: bool = Field(True, description="Return audio as base64 encoded string")

class VideoUploadRequest(BaseModel):
   """Request model for video file upload"""

   user_id: Optional[str] = Field(None, description="User identifier (if not provided, generated from session)")
"""Response models for API endpoints"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class SrtDetail(BaseModel):
   """Detailed subtitle information with coordinates"""

   srt: str  # Content of subtitle
   srt_time: str  # Time in SRT format (HH:MM:SS,mmm --> HH:MM:SS,mmm)
   x1: float  # X coordinate of top-left corner
   y1: float  # Y coordinate of top-left corner
   x2: float  # X coordinate of bottom-right corner
   y2: float  # Y coordinate of bottom-right corner


class ExtractResponse(BaseModel):
   """Response model for subtitle extraction"""

   srt: str
   srt_detail: List[SrtDetail] = []
   stats: Dict[str, Any]
   srt_output_path: Optional[str] = Field(None, description="Path where SRT file was saved (if auto-saved)")


class TaskStatusResponse(BaseModel):
   """Response model for async task status"""

   task_id: str
   status: str
   progress: Optional[float] = None
   result: Optional[ExtractResponse] = None
   error: Optional[str] = None


class TTSGenerateResponse(BaseModel):
   """Response model for TTS audio synthesis"""

   task_id: str = Field(..., description="Unique task identifier")
   status: str = Field("success", description="Operation status")
   audio_id: str = Field(..., description="Unique audio identifier (GUID)")
   audio_base64: Optional[str] = Field(None, description="Base64 encoded audio data")
   duration_ms: float = Field(..., description="Audio duration in milliseconds")
   size_bytes: int = Field(..., description="Audio file size in bytes")
   message: Optional[str] = Field(None, description="Additional message or error details")


class VideoUploadResponse(BaseModel):
   """Response model for video upload"""

   id: str = Field(..., description="Unique video GUID")
   user_id: str = Field(..., description="User identifier")
   filename: str = Field(..., description="Original filename")
   file_size: int = Field(..., description="File size in bytes")
   created_at: str = Field(..., description="Upload timestamp (ISO format)")
   status: str = Field("success", description="Upload status")
   message: Optional[str] = Field(None, description="Additional message")


class UserQuotaResponse(BaseModel):
   """Response model for user quota information"""

   user_id: str = Field(..., description="User identifier")
   video_count: int = Field(..., description="Number of non-deleted videos")
   max_videos: int = Field(..., description="Maximum videos allowed per user")
   remaining_quota: int = Field(..., description="Remaining videos before cleanup")
   total_size_bytes: int = Field(..., description="Total size of all videos in bytes")
   last_updated: str = Field(..., description="Last quota update timestamp (ISO format)")

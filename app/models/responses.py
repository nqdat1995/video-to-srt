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
   audio_filename: str = Field(..., description="Generated audio filename")
   audio_path: str = Field(..., description="Full path to generated audio file")
   audio_base64: Optional[str] = Field(None, description="Base64 encoded audio data")
   duration_ms: float = Field(..., description="Audio duration in milliseconds")
   size_bytes: int = Field(..., description="Audio file size in bytes")
   message: Optional[str] = Field(None, description="Additional message or error details")
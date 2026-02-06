"""Response models for API endpoints"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel


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
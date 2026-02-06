"""Response models for API endpoints"""

from typing import Optional, Dict, Any
from pydantic import BaseModel


class ExtractResponse(BaseModel):
   """Response model for subtitle extraction"""

   srt: str
   stats: Dict[str, Any]


class TaskStatusResponse(BaseModel):
   """Response model for async task status"""

   task_id: str
   status: str
   progress: Optional[float] = None
   result: Optional[ExtractResponse] = None
   error: Optional[str] = None
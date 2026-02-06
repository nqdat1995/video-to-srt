"""API route handlers"""

import time
import threading
import uuid
from typing import Dict

from fastapi import APIRouter, HTTPException, BackgroundTasks

from ..models.requests import ExtractRequest, BlurAndSubtitleRequest, BlurRequest, SubtitleRequest
from ..models.responses import ExtractResponse, TaskStatusResponse
from ..services.video_processor import video_processor

router = APIRouter()

# Task tracking storage (in production, use Redis or database)
_TASKS: Dict[str, dict] = {}
_TASKS_LOCK = threading.Lock()


@router.get("/health")
def health():
   """Health check endpoint"""
   return {"status": "ok"}


@router.post("/extract-srt", response_model=ExtractResponse)
def extract_srt(req: ExtractRequest):
   """
   Synchronous subtitle extraction endpoint

   Args:
       req: Extraction request

   Returns:
       Extraction response with SRT and stats
   """
   return video_processor.process_video(req)


@router.post("/blur")
def blur(req: BlurRequest):
   """
   Blur regions in video based on coordinates

   Args:
       req: Blur request

   Returns:
       Response with output video path and stats
   """
   try:
       result = video_processor.blur_video(req)
       return {
           "status": "success",
           "data": result
       }
   except FileNotFoundError as e:
       raise HTTPException(status_code=404, detail=str(e))
   except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))


@router.post("/subtitle")
def subtitle(req: SubtitleRequest):
   """
   Add SRT subtitles to video

   Args:
       req: Subtitle request

   Returns:
       Response with output video path and stats
   """
   try:
       result = video_processor.add_subtitles(req)
       return {
           "status": "success",
           "data": result
       }
   except FileNotFoundError as e:
       raise HTTPException(status_code=404, detail=str(e))
   except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))


@router.post("/blur-and-subtitle")
def blur_and_subtitle(req: BlurAndSubtitleRequest):
   """
   Blur original subtitles and add new SRT to video (combined operation)

   Args:
       req: Blur and subtitle request

   Returns:
       Response with output video path and stats
   """
   try:
       result = video_processor.blur_and_add_subtitles(req)
       return {
           "status": "success",
           "data": result
       }
   except FileNotFoundError as e:
       raise HTTPException(status_code=404, detail=str(e))
   except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-srt-async")
async def extract_srt_async(req: ExtractRequest, background_tasks: BackgroundTasks):
   """
   Asynchronous subtitle extraction endpoint with progress tracking

   Args:
       req: Extraction request
       background_tasks: FastAPI background tasks

   Returns:
       Task ID and status
   """
   task_id = str(uuid.uuid4())

   # Initialize task
   with _TASKS_LOCK:
       _TASKS[task_id] = {
           "status": "processing",
           "progress": 0.0,
           "result": None,
           "error": None,
           "created_at": time.time()
       }

   # Add background task
   background_tasks.add_task(_process_video_background, task_id, req)

   return {
       "task_id": task_id,
       "status": "processing",
       "message": "Task started. Use GET /task/{task_id} to check status."
   }


def _process_video_background(task_id: str, req: ExtractRequest):
   """Background task for video processing"""

   def update_progress(progress: float):
       with _TASKS_LOCK:
           if task_id in _TASKS:
               _TASKS[task_id]["progress"] = progress

   try:
       result = video_processor.process_video(req, progress_callback=update_progress)
       with _TASKS_LOCK:
           if task_id in _TASKS:
               _TASKS[task_id]["status"] = "completed"
               _TASKS[task_id]["result"] = result
               _TASKS[task_id]["progress"] = 1.0
   except Exception as e:
       with _TASKS_LOCK:
           if task_id in _TASKS:
               _TASKS[task_id]["status"] = "failed"
               _TASKS[task_id]["error"] = str(e)


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
   """
   Get status of async task

   Args:
       task_id: Task identifier

   Returns:
       Task status response
   """
   with _TASKS_LOCK:
       if task_id not in _TASKS:
           raise HTTPException(status_code=404, detail="Task not found")

       task = _TASKS[task_id]
       return TaskStatusResponse(
           task_id=task_id,
           status=task["status"],
           progress=task.get("progress"),
           result=task.get("result"),
           error=task.get("error")
       )


@router.delete("/task/{task_id}")
async def delete_task(task_id: str):
   """
   Delete task from tracking (cleanup)

   Args:
       task_id: Task identifier

   Returns:
       Deletion confirmation
   """
   with _TASKS_LOCK:
       if task_id in _TASKS:
           del _TASKS[task_id]
           return {"message": "Task deleted"}
       raise HTTPException(status_code=404, detail="Task not found")

"""API route handlers"""

import time
import threading
import uuid
import os
from typing import Dict

from fastapi import APIRouter, HTTPException, BackgroundTasks

from ..models.requests import (
    ExtractRequest,
    BlurAndSubtitleRequest,
    BlurRequest,
    SubtitleRequest,
    TTSGenerateRequest,
)
from ..models.responses import ExtractResponse, TaskStatusResponse, TTSGenerateResponse
from ..services.video_processor import video_processor
from ..services.tts_service import (
    TTSService,
    parse_srt_content,
    merge_wav_files,
    TTSError,
)
from ..core.config import settings

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


@router.post("/extract-srt-frames", response_model=ExtractResponse)
def extract_srt_frames(req: ExtractRequest):
    """
    Synchronous full-FPS subtitle extraction: runs OCR on every sampled frame

    This endpoint samples frames at `target_fps` and runs OCR on each sampled
    frame. Consecutive sampled frames with identical or similar OCR text
    (based on `sim_thr`) are merged into a single SRT cue.
    """
    return video_processor.process_video_fullfps(req)


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
        return {"status": "success", "data": result}
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
        return {"status": "success", "data": result}
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
        return {"status": "success", "data": result}
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
            "created_at": time.time(),
        }

    # Add background task
    background_tasks.add_task(_process_video_background, task_id, req)

    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Task started. Use GET /task/{task_id} to check status.",
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
            error=task.get("error"),
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


@router.post("/tts/generate", response_model=TTSGenerateResponse)
def tts_generate(req: TTSGenerateRequest):
    """
    Generate audio from SRT subtitles using TTS

    This endpoint:
    1. Parses SRT content into subtitle blocks
    2. Downloads audio files from TTS API for each subtitle
    3. Merges audio files in correct order based on SRT timeline
    4. Returns the merged audio (optionally as base64)

    Args:
        req: TTS generation request

    Returns:
        TTS response with audio file path and optional base64 data

    Raises:
        HTTPException: If TTS is disabled or operation fails
    """
    if not settings.TTS_ENABLED:
        raise HTTPException(status_code=503, detail="TTS service is not enabled")

    try:
        task_id = str(uuid.uuid4())

        # Ensure output directories exist
        os.makedirs(settings.TTS_OUTPUT_DIR, exist_ok=True)
        os.makedirs(settings.TTS_TEMP_DIR, exist_ok=True)

        # Parse SRT content
        subtitles = parse_srt_content(req.srt_content)
        if not subtitles:
            raise ValueError("Invalid SRT content or empty")

        # Create temporary directory for this task
        task_temp_dir = os.path.join(settings.TTS_TEMP_DIR, task_id)
        os.makedirs(task_temp_dir, exist_ok=True)

        # Initialize TTS service
        tts_service = TTSService(
            tts_voice=req.tts_voice,
            api_key=settings.TTS_API_KEY,
            api_token=settings.TTS_API_TOKEN,
        )

        # Download audio files
        tts_service.download_wav_from_srt(
            task_temp_dir,
            subtitles,
            batch_size=settings.TTS_BATCH_SIZE,
            max_retries=settings.TTS_MAX_RETRIES,
        )

        # Get list of downloaded WAV files sorted by sequence
        wav_files = []
        for subtitle in subtitles:
            seq = subtitle["sequence"]
            wav_path = os.path.join(task_temp_dir, "textReading", f"{seq}.wav")
            if os.path.exists(wav_path):
                wav_files.append(wav_path)

        if not wav_files:
            raise ValueError("No audio files were generated")

        # Generate output filename
        output_filename = req.output_filename or f"tts_audio_{task_id[:8]}.wav"
        output_path = os.path.join(settings.TTS_OUTPUT_DIR, output_filename)

        # Merge audio files
        audio_base64_merged = merge_wav_files(wav_files, output_path, subtitles)

        # Get file info
        file_size = os.path.getsize(output_path)

        # Calculate duration
        duration_ms = 0
        try:
            import subprocess

            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.stdout.strip():
                duration_ms = float(result.stdout.strip()) * 1000
        except Exception:
            duration_ms = 0

        # Use base64 from merge if requested, otherwise encode separately
        audio_base64 = None
        if req.return_base64:
            audio_base64 = audio_base64_merged

        # Cleanup temporary directory
        import shutil

        try:
            shutil.rmtree(task_temp_dir)
        except Exception:
            pass

        return TTSGenerateResponse(
            task_id=task_id,
            status="success",
            audio_filename=output_filename,
            audio_path=output_path,
            audio_base64=audio_base64,
            duration_ms=duration_ms,
            size_bytes=file_size,
            message="Audio synthesis completed successfully",
        )

    except TTSError as e:
        raise HTTPException(status_code=500, detail=f"TTS Error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

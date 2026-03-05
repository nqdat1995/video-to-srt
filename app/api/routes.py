"""API route handlers"""

import time
import threading
import uuid
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Depends, Query
from sqlalchemy.orm import Session

from ..models.requests import (
    ExtractRequest,
    BlurAndSubtitleRequest,
    BlurRequest,
    SubtitleRequest,
    TTSGenerateRequest,
    MergeVideoRequest,
)
from ..models.responses import (
    ExtractResponse,
    TaskStatusResponse,
    TTSGenerateResponse,
    VideoUploadResponse,
    UserQuotaResponse,
    MergeVideoResponse,
)
from ..services.video_processor import video_processor
from ..services.tts_service import (
    TTSService,
    parse_srt_content,
    merge_wav_files,
    TTSError,
)
from ..services.storage_service import storage_service
from ..services.database_service import database_service
from ..core.config import settings
from ..core.database import get_db

router = APIRouter()

# Task tracking storage (in production, use Redis or database)
_TASKS: Dict[str, dict] = {}
_TASKS_LOCK = threading.Lock()


@router.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok"}


@router.post("/extract-srt", response_model=ExtractResponse)
def extract_srt(req: ExtractRequest, db: Session = Depends(get_db)):
    """
    Synchronous subtitle extraction endpoint

    Args:
        req: Extraction request
        db: Database session

    Returns:
        Extraction response with SRT and stats
    """
    # Determine which video path to use
    video_path = None
    
    if req.video_id:
        # Priority 1: video_id - fetch from database
        video = database_service.get_video_by_id(db, req.video_id, include_deleted=False)
        
        if not video:
            raise HTTPException(
                status_code=404,
                detail=f"Video with ID {req.video_id} not found or has been deleted"
            )
        video_path = video.file_path
        original_filename = video.filename
    elif req.video:
        # Priority 2: video - use provided path
        video_path = req.video
        original_filename = None
    else:
        raise HTTPException(
            status_code=400,
            detail="Either video_id or video must be provided"
        )
    
    # Process video
    result = video_processor.process_video(
        req, 
        video_path=video_path,
        original_filename=original_filename,
        auto_save_srt=(req.video_id is not None)
    )
    return result


@router.post("/extract-srt-frames", response_model=ExtractResponse)
def extract_srt_frames(req: ExtractRequest, db: Session = Depends(get_db), background_tasks: BackgroundTasks = BackgroundTasks()):
    """
    Full-FPS subtitle extraction with caching and async support.
    
    Features:
    - Runs OCR on every sampled frame
    - Caches results in database with configurable expiry
    - Supports async background execution
    - Prevents duplicate concurrent extractions via request locking
    
    Args:
        req: Extraction request
        db: Database session
        background_tasks: FastAPI background tasks
        
    Returns:
        Extraction response with SRT and cache status
    """
    # Determine which video path to use
    video_path = None
    video_id = None
    
    if req.video_id:
        # Priority 1: video_id - fetch from database
        video = database_service.get_video_by_id(db, req.video_id, include_deleted=False)
        
        if not video:
            raise HTTPException(
                status_code=404,
                detail=f"Video with ID {req.video_id} not found or has been deleted"
            )
        video_path = video.file_path
        video_id = req.video_id
        original_filename = video.filename
    elif req.video:
        # Priority 2: video - use provided path
        video_path = req.video
        original_filename = None
    else:
        raise HTTPException(
            status_code=400,
            detail="Either video_id or video must be provided"
        )
    
    # Check cache if force_extract is False and we have video_id
    if video_id and not req.force_extract:
        cached_result = database_service.get_cached_extraction(db, video_id)
        if cached_result:
            srt, srt_detail_list, srt_output_path = cached_result
            
            # Reconstruct the stats from cache (basic stats)
            return ExtractResponse(
                srt=srt,
                srt_detail=srt_detail_list if isinstance(srt_detail_list, list) and srt_detail_list and hasattr(srt_detail_list[0], 'model_dump') else srt_detail_list,
                stats={"cache_hit": True, "cached": True},
                srt_output_path=srt_output_path,
                task_id=None,
                is_cached=True
            )
    
    # Handle async execution
    if req.execute_async:
        task_id = str(uuid.uuid4())
        
        # Initialize task tracking
        with _TASKS_LOCK:
            _TASKS[task_id] = {
                "status": "processing",
                "progress": 0.0,
                "result": None,
                "error": None,
                "created_at": time.time(),
                "video_id": video_id,
            }
        
        # Queue background task
        background_tasks.add_task(
            _process_extraction_background,
            task_id=task_id,
            video_id=video_id,
            req=req,
            video_path=video_path,
            original_filename=original_filename,
            db_session_maker=None,  # Will create new session in background task
        )
        
        # Return immediately with task info
        return ExtractResponse(
            srt="",
            srt_detail=[],
            stats={},
            srt_output_path=None,
            task_id=task_id,
            is_cached=False
        )
    
    # Synchronous execution
    if video_id:
        # Try to acquire extraction lock
        request_id = str(uuid.uuid4())
        try:
            database_service.set_extraction_request_id(db, video_id, request_id)
            db.commit()  # Persist lock to database immediately
        except HTTPException:
            # Already locked, return 409
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
    
    try:
        # Process video with full-fps mode
        result = video_processor.process_video_fullfps(
            req, 
            video_path=video_path,
            original_filename=original_filename,
            auto_save_srt=(video_id is not None)
        )
        
        # Save extraction result to database
        if video_id and result:
            database_service.save_extraction_result(
                db=db,
                video_id=video_id,
                srt=result.srt,
                srt_detail_list=result.srt_detail,
                srt_output_path=result.srt_output_path,
            )
            db.commit()
        
        # Add task_id and is_cached fields to response
        result.task_id = None
        result.is_cached = False
        
        return result
        
    except Exception as e:
        # Clear lock on error
        if video_id:
            database_service.clear_extraction_request_id(db, video_id)
            db.commit()
        raise
    finally:
        # Ensure lock is cleared (in case of unexpected error)
        if video_id:
            try:
                database_service.clear_extraction_request_id(db, video_id)
                db.commit()
            except:
                pass


def _process_extraction_background(
    task_id: str,
    video_id: Optional[str],
    req: ExtractRequest,
    video_path: str,
    original_filename: Optional[str],
    db_session_maker,
) -> None:
    """
    Background task for async extraction.
    
    Args:
        task_id: Unique task identifier
        video_id: Optional video ID for database persistence
        req: Extraction request
        video_path: Path to video file
        original_filename: Optional original filename
        db_session_maker: Database session factory (unused, creates new session)
    """
    from ..core.database import SessionLocal
    
    db = None
    request_id = str(uuid.uuid4())
    
    try:
        db = SessionLocal()
        
        # Acquire extraction lock
        if video_id:
            try:
                database_service.set_extraction_request_id(db, video_id, request_id)
                db.commit()  # Persist lock to database immediately
            except HTTPException as e:
                # Already locked
                db.rollback()
                with _TASKS_LOCK:
                    if task_id in _TASKS:
                        _TASKS[task_id]["status"] = "failed"
                        _TASKS[task_id]["error"] = f"Extraction already in progress for this video"
                return
            except Exception as e:
                db.rollback()
                with _TASKS_LOCK:
                    if task_id in _TASKS:
                        _TASKS[task_id]["status"] = "failed"
                        _TASKS[task_id]["error"] = str(e)
                return
        
        # Process video with progress callback
        def update_progress(progress: float):
            with _TASKS_LOCK:
                if task_id in _TASKS:
                    _TASKS[task_id]["progress"] = progress
        
        result = video_processor.process_video_fullfps(
            req,
            video_path=video_path,
            original_filename=original_filename,
            auto_save_srt=(video_id is not None),
            progress_callback=update_progress,
        )
        
        # Save extraction result to database
        if video_id and result:
            database_service.save_extraction_result(
                db=db,
                video_id=video_id,
                srt=result.srt,
                srt_detail_list=result.srt_detail,
                srt_output_path=result.srt_output_path,
            )
            db.commit()
        
        # Update task status
        result.task_id = task_id
        result.is_cached = False
        
        with _TASKS_LOCK:
            if task_id in _TASKS:
                _TASKS[task_id]["status"] = "completed"
                _TASKS[task_id]["result"] = result
                _TASKS[task_id]["progress"] = 1.0
                
    except Exception as e:
        # Log error and update task status
        error_msg = f"{type(e).__name__}: {str(e)}"
        
        # Clear lock on error
        if video_id:
            try:
                database_service.clear_extraction_request_id(db, video_id)
                if db:
                    db.commit()
            except:
                pass
        
        with _TASKS_LOCK:
            if task_id in _TASKS:
                _TASKS[task_id]["status"] = "failed"
                _TASKS[task_id]["error"] = error_msg
                
    finally:
        # Ensure lock is cleared
        if video_id:
            try:
                database_service.clear_extraction_request_id(db, video_id)
                if db:
                    db.commit()
            except:
                pass
        
        # Close database session
        if db:
            try:
                db.close()
            except:
                pass



@router.post("/blur")
def blur(req: BlurRequest, db: Session = Depends(get_db)):
    """
    Blur regions in video based on coordinates

    Args:
        req: Blur request
        db: Database session

    Returns:
        Response with new video ID (output video saved to database)
    """
    try:
        # Determine which video path to use and get user_id
        video_path = None
        user_id = None
        
        if req.video_id:
            # Priority 1: video_id - fetch from database
            video = database_service.get_video_by_id(db, req.video_id, include_deleted=False)
            if not video:
                raise HTTPException(
                    status_code=404,
                    detail=f"Video with ID {req.video_id} not found or has been deleted"
                )
            video_path = video.file_path
            user_id = video.user_id
        elif req.video_path:
            # Priority 2: video_path - use provided path
            video_path = req.video_path
            # Generate a user_id if not available (for local files)
            user_id = str(uuid.uuid4())
        else:
            raise HTTPException(
                status_code=400,
                detail="Either video_id or video_path must be provided"
            )
        
        # Create a modified request with resolved video_path
        modified_req = BlurRequest(
            video_path=video_path,
            video_id=None,
            srt_detail=req.srt_detail,
            blur_strength=req.blur_strength,
            blur_expansion_percent=req.blur_expansion_percent,
            output_suffix=req.output_suffix,
            use_gpu=req.use_gpu
        )
        
        result = video_processor.blur_video(modified_req)
        output_path = result["output_path"]
        
        # Save output video to database
        output_file_path = Path(output_path)
        output_file_size = output_file_path.stat().st_size if output_file_path.exists() else 0
        output_video_id = str(uuid.uuid4())
        
        output_video = storage_service.save_video(
            db=db,
            video_id=output_video_id,
            user_id=user_id,
            file_path=str(output_path),
            original_filename=f"{output_file_path.stem}_blurred{output_file_path.suffix}",
            file_size=output_file_size,
        )
        
        return {
            "status": "success",
            "video_id": output_video.id,
            "blur_strength": req.blur_strength,
            "blur_expansion_percent": req.blur_expansion_percent,
            "srt_count": len(req.srt_detail) if req.srt_detail else 0,
            "gpu_acceleration": result.get("gpu_acceleration", False),
            "message": "Video blurred successfully"
        }
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subtitle")
def subtitle(req: SubtitleRequest, db: Session = Depends(get_db)):
    """
    Add SRT subtitles to video

    Args:
        req: Subtitle request
        db: Database session

    Returns:
        Response with new video ID (output video saved to database)
    """
    try:
        # Determine which video path to use and get user_id
        video_path = None
        user_id = None
        
        if req.video_id:
            # Priority 1: video_id - fetch from database
            video = database_service.get_video_by_id(db, req.video_id, include_deleted=False)
            if not video:
                raise HTTPException(
                    status_code=404,
                    detail=f"Video with ID {req.video_id} not found or has been deleted"
                )
            video_path = video.file_path
            user_id = video.user_id
        elif req.video_path:
            # Priority 2: video_path - use provided path
            video_path = req.video_path
            # Generate a user_id if not available (for local files)
            user_id = str(uuid.uuid4())
        else:
            raise HTTPException(
                status_code=400,
                detail="Either video_id or video_path must be provided"
            )
        
        # Write srt_content to temporary file (or convert to ASS if fontname/fontsize/y_position provided)
        from ..services.srt_service import srt_service
        srt_content = req.srt_content
        if req.fontname != "Arial" or req.fontsize != 10 or req.subtitle_y_position != 90:
            # Convert to ASS format with styling
            srt_content = srt_service.srt_to_ass(req.srt_content, req.fontname, req.fontsize, req.subtitle_y_position)
            temp_srt_path = _create_temp_subtitle_file(srt_content, "ass")
        else:
            temp_srt_path = _create_temp_srt_file(req.srt_content)
        
        try:
            # Set the resolved paths
            req.video_path = video_path
            req.srt_path = temp_srt_path
            
            result = video_processor.add_subtitles(req)
            output_path = result["output_path"]
            
            # Save output video to database
            output_file_path = Path(output_path)
            output_file_size = output_file_path.stat().st_size if output_file_path.exists() else 0
            output_video_id = str(uuid.uuid4())
            
            output_video = storage_service.save_video(
                db=db,
                video_id=output_video_id,
                user_id=user_id,
                file_path=str(output_path),
                original_filename=f"{output_file_path.stem}{output_file_path.suffix}",
                file_size=output_file_size,
            )
            
            return {
                "status": "success",
                "video_id": output_video.id,
                "fontname": req.fontname,
                "fontsize": req.fontsize,
                "subtitle_y_position": req.subtitle_y_position,
                "gpu_acceleration": result.get("gpu_acceleration", False),
                "message": "Subtitles added successfully"
            }
        finally:
            # Clean up temporary SRT file
            _cleanup_temp_srt_file(temp_srt_path)
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/blur-and-subtitle")
def blur_and_subtitle(req: BlurAndSubtitleRequest, db: Session = Depends(get_db)):
    """
    Blur original subtitles and add new SRT to video (combined operation)

    Args:
        req: Blur and subtitle request
        db: Database session

    Returns:
        Response with new video ID (output video saved to database)
    """
    try:
        # Determine which video path to use and get user_id
        video_path = None
        user_id = None
        
        if req.video_id:
            # Priority 1: video_id - fetch from database
            video = database_service.get_video_by_id(db, req.video_id, include_deleted=False)
            if not video:
                raise HTTPException(
                    status_code=404,
                    detail=f"Video with ID {req.video_id} not found or has been deleted"
                )
            video_path = video.file_path
            user_id = video.user_id
        elif req.video_path:
            # Priority 2: video_path - use provided path
            video_path = req.video_path
            # Generate a user_id if not available (for local files)
            user_id = str(uuid.uuid4())
        else:
            raise HTTPException(
                status_code=400,
                detail="Either video_id or video_path must be provided"
            )
        
        # Write srt_content to temporary file (or convert to ASS if fontname/fontsize/y_position provided)
        from ..services.srt_service import srt_service
        srt_content = req.srt_content
        if req.fontname != "Arial" or req.fontsize != 10 or req.subtitle_y_position != 90:
            # Convert to ASS format with styling
            srt_content = srt_service.srt_to_ass(req.srt_content, req.fontname, req.fontsize, req.subtitle_y_position)
            temp_srt_path = _create_temp_subtitle_file(srt_content, "ass")
        else:
            temp_srt_path = _create_temp_srt_file(req.srt_content)
        
        try:
            # Set the resolved paths
            req.video_path = video_path
            req.srt_path = temp_srt_path
            
            result = video_processor.blur_and_add_subtitles(req)
            output_path = result["output_path"]
            
            # Save output video to database
            output_file_path = Path(output_path)
            output_file_size = output_file_path.stat().st_size if output_file_path.exists() else 0
            output_video_id = str(uuid.uuid4())
            
            output_video = storage_service.save_video(
                db=db,
                video_id=output_video_id,
                user_id=user_id,
                file_path=str(output_path),
                original_filename=f"{output_file_path.stem}_vnsrt{output_file_path.suffix}",
                file_size=output_file_size,
            )
            
            return {
                "status": "success",
                "video_id": output_video.id,
                "blur_strength": req.blur_strength,
                "blur_expansion_percent": req.blur_expansion_percent,
                "fontname": req.fontname,
                "fontsize": req.fontsize,
                "subtitle_y_position": req.subtitle_y_position,
                "srt_count": len(req.srt_detail) if req.srt_detail else 0,
                "gpu_acceleration": result.get("gpu_acceleration", False),
                "message": "Video blurred and subtitled successfully"
            }
        finally:
            # Clean up temporary SRT file
            _cleanup_temp_srt_file(temp_srt_path)
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/merge-video", response_model=MergeVideoResponse)
def merge_video(req: MergeVideoRequest, db: Session = Depends(get_db)):
    """
    Merge video with audio from TTS or other sources

    Merges a video file with an audio file, allowing control over:
    - Volume level of the video's original audio (0-100, where 0=mute, 100=preserve)
    - Audio duration scaling (if True, stretches/compresses audio to match video duration)

    Args:
        req: Merge video request with video_id, audio_id, volume_level, scale_audio_duration
        db: Database session

    Returns:
        Response with new merged video ID saved to database
    """
    try:
        # Fetch video from database
        video = database_service.get_video_by_id(db, req.video_id, include_deleted=False)
        if not video:
            raise HTTPException(
                status_code=404,
                detail=f"Video with ID {req.video_id} not found or has been deleted"
            )
        video_path = video.file_path
        user_id = video.user_id

        # Fetch audio from database
        audio = database_service.get_audio_by_id(db, req.audio_id, include_deleted=False)
        if not audio:
            raise HTTPException(
                status_code=404,
                detail=f"Audio with ID {req.audio_id} not found or has been deleted"
            )
        audio_path = audio.file_path

        # Generate unique output filename using GUID (like uploads/{video_id}.mp4)
        output_video_id = str(uuid.uuid4())
        video_extension = Path(video_path).suffix
        
        # Determine output directory
        output_dir = Path(settings.UPLOAD_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create output file path with GUID-based naming for uniqueness
        output_file_path_str = str(output_dir / f"{output_video_id}{video_extension}")

        # Merge video and audio with custom output path
        result = video_processor.merge_video(
            video_path=video_path,
            audio_path=audio_path,
            volume_level=req.volume_level,
            scale_audio_duration=req.scale_audio_duration,
            output_path=output_file_path_str,
        )
        
        # Verify output file exists and get size
        output_file_path = Path(output_file_path_str)
        output_file_size = output_file_path.stat().st_size if output_file_path.exists() else 0

        output_video = storage_service.save_video(
            db=db,
            video_id=output_video_id,
            user_id=user_id,
            file_path=output_file_path_str,
            original_filename=f"{output_video_id}{video_extension}",
            file_size=output_file_size,
        )

        return MergeVideoResponse(
            video_id=output_video.id,
            status="success",
            file_size=output_file_size,
            output_filename=f"{output_video_id}{video_extension}",
            volume_level=req.volume_level,
            scale_audio_duration=req.scale_audio_duration,
            message=result.get("message"),
        )
    except HTTPException:
        raise
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
def tts_generate(req: TTSGenerateRequest, db: Session = Depends(get_db)):
    """
    Generate audio from SRT subtitles using TTS

    This endpoint:
    1. Parses SRT content into subtitle blocks
    2. Downloads audio files from TTS API for each subtitle
    3. Merges audio files in correct order based on SRT timeline
    4. Stores audio metadata and file in database
    5. Returns the merged audio (optionally as base64)

    Args:
        req: TTS generation request
        db: Database session

    Returns:
        TTS response with audio_id instead of file paths

    Raises:
        HTTPException: If TTS is disabled or operation fails
    """
    if not settings.TTS_ENABLED:
        raise HTTPException(status_code=503, detail="TTS service is not enabled")

    try:
        task_id = str(uuid.uuid4())
        audio_id = str(uuid.uuid4())
        user_id = req.user_id or "anonymous"

        # Ensure output directories exist
        os.makedirs(settings.TTS_OUTPUT_DIR, exist_ok=True)
        os.makedirs(settings.AUDIO_OUTPUT_DIR, exist_ok=True)
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

        # Generate output filename with audio_id
        output_filename = f"{audio_id}.wav"
        output_path = os.path.join(settings.AUDIO_OUTPUT_DIR, output_filename)

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

        # Save audio metadata to database
        audio = storage_service.save_audio(
            db=db,
            audio_id=audio_id,
            user_id=user_id,
            file_path=output_path,
            filename=output_filename,
            file_size=file_size,
            duration_ms=duration_ms,
        )

        # Use base64 from merge if requested, otherwise None
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
            audio_id=audio_id,
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

@router.post("/upload-video", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    user_id: str = None,
    db: Session = Depends(get_db),
):
    """
    Upload a video file with quota management.
    
    - Stores file in UPLOAD_DIR with GUID-based naming
    - Stores metadata in PostgreSQL database
    - Automatically deletes oldest videos if user exceeds MAX_VIDEOS_PER_USER
    - Marks deleted videos with is_deleted flag in database

    Args:
        file: Video file to upload
        user_id: Optional user identifier (if not provided, generates a new GUID)
        db: Database session

    Returns:
        VideoUploadResponse with video ID (GUID) and metadata
    """
    try:
        # Generate user_id if not provided
        if not user_id:
            user_id = str(uuid.uuid4())

        # Validate file format
        file_ext = Path(file.filename).suffix.lower().lstrip(".")
        if file_ext not in settings.ALLOWED_VIDEO_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file format. Allowed formats: {', '.join(settings.ALLOWED_VIDEO_FORMATS)}",
            )

        # Read file and validate size
        file_content = await file.read()
        file_size = len(file_content)

        max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
            )

        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="File is empty",
            )

        # Generate GUID for video
        video_id = str(uuid.uuid4())

        # Save file to disk with GUID-based naming
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / f"{video_id}.{file_ext}"
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Save metadata to database (handles quota management and cleanup)
        video = storage_service.save_video(
            db=db,
            video_id=video_id,
            user_id=user_id,
            file_path=str(file_path),
            original_filename=file.filename,
            file_size=file_size,
        )

        return VideoUploadResponse(
            id=video.id,
            user_id=video.user_id,
            filename=video.filename,
            file_size=video.file_size,
            created_at=video.created_at.isoformat(),
            status="success",
            message=f"Video uploaded successfully. ID: {video_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload video: {str(e)}",
        )


@router.get("/user/{user_id}/quota", response_model=UserQuotaResponse)
def get_user_quota(user_id: str, db: Session = Depends(get_db)):
    """
    Get user's current upload quota and usage.

    Args:
        user_id: User identifier
        db: Database session

    Returns:
        UserQuotaResponse with quota information
    """
    try:
        user_quota = storage_service.get_user_quota(db, user_id)

        if not user_quota:
            return UserQuotaResponse(
                user_id=user_id,
                video_count=0,
                max_videos=settings.MAX_VIDEOS_PER_USER,
                remaining_quota=settings.MAX_VIDEOS_PER_USER,
                total_size_bytes=0,
                last_updated=datetime.utcnow().isoformat(),
            )

        remaining_quota = max(
            0,
            settings.MAX_VIDEOS_PER_USER - user_quota.video_count,
        )

        return UserQuotaResponse(
            user_id=user_quota.user_id,
            video_count=user_quota.video_count,
            max_videos=settings.MAX_VIDEOS_PER_USER,
            remaining_quota=remaining_quota,
            total_size_bytes=user_quota.total_size_bytes,
            last_updated=user_quota.last_updated.isoformat(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get quota: {str(e)}",
        )


@router.get("/user/{user_id}/videos")
def get_user_videos(
    user_id: str,
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Get all videos for a user.

    Args:
        user_id: User identifier
        include_deleted: Whether to include soft-deleted videos (query param)
        db: Database session

    Returns:
        List of videos
    """
    try:
        videos = storage_service.get_user_videos(db, user_id, include_deleted)
        return {
            "user_id": user_id,
            "total_count": len(videos),
            "videos": [
                {
                    "id": v.id,
                    "filename": v.filename,
                    "file_size": v.file_size,
                    "created_at": v.created_at.isoformat(),
                    "is_deleted": v.is_deleted,
                    "deleted_at": v.deleted_at.isoformat() if v.deleted_at else None,
                }
                for v in videos
            ],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get videos: {str(e)}",
        )


@router.delete("/video/{video_id}")
def delete_video(
    video_id: str,
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Delete a video (soft delete by default).

    Args:
        video_id: Video GUID
        user_id: User identifier for permission check (query param)
        db: Database session

    Returns:
        Success message
    """
    try:
        success = storage_service.delete_video(db, video_id, user_id, hard_delete=True)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Video not found or not authorized",
            )
        return {
            "status": "success",
            "message": f"Video {video_id} deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete video: {str(e)}",
        )


def _create_temp_srt_file(srt_content: str) -> str:
    """
    Create a temporary SRT file from content string

    Args:
        srt_content: SRT subtitle content

    Returns:
        Path to the temporary SRT file

    Raises:
        ValueError: If srt_content is empty
    """
    if not srt_content or not srt_content.strip():
        raise ValueError("SRT content cannot be empty")
    
    # Ensure temp directory exists
    temp_dir = Path(settings.SRT_TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    temp_filename = f"srt_{uuid.uuid4()}.srt"
    temp_srt_path = temp_dir / temp_filename
    
    # Write content to file
    with open(temp_srt_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)
    
    return str(temp_srt_path)


def _create_temp_subtitle_file(content: str, format: str = "srt") -> str:
    """
    Create a temporary subtitle file from content string

    Args:
        content: Subtitle content
        format: File format (srt, ass, sub, etc.)

    Returns:
        Path to the temporary subtitle file

    Raises:
        ValueError: If content is empty
    """
    if not content or not content.strip():
        raise ValueError("Subtitle content cannot be empty")
    
    # Ensure temp directory exists
    temp_dir = Path(settings.SRT_TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    temp_filename = f"srt_{uuid.uuid4()}.{format}"
    temp_path = temp_dir / temp_filename
    
    # Write content to file
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return str(temp_path)


def _cleanup_temp_srt_file(temp_srt_path: str) -> None:
    """
    Clean up temporary SRT file

    Args:
        temp_srt_path: Path to the temporary SRT file
    """
    try:
        if temp_srt_path and os.path.exists(temp_srt_path):
            os.remove(temp_srt_path)
    except Exception:
        # Silently ignore cleanup errors
        pass
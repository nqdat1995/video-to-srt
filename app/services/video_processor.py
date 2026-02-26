"""Video processing service"""
import os
import time
from typing import List, Optional, Tuple, Callable, Dict, Any
from collections import Counter

import cv2
import numpy as np

from ..models.requests import (
    ExtractRequest,
    BlurAndSubtitleRequest,
    BlurRequest,
    SubtitleRequest,
)
from ..models.responses import ExtractResponse
from ..models.internal import CueDraft
from ..services.ocr_service import ocr_service
from ..services.ffmpeg_service import ffmpeg_service
from ..services.srt_service import srt_service
from ..utils.hash_utils import ahash, hamming64
from ..utils.image_utils import (
    detect_active_vertical_region, 
    enhance_roi, 
    detect_subtitle_region,
    detect_roi_content_change,
    detect_text_motion,
    detect_text_presence_change,
    detect_intensity_spike
)
from ..utils.text_utils import normalize_text, similarity, strip_quotes
from ..core.config import settings


class VideoProcessor:
    """Service for processing videos and extracting subtitles"""

    def __init__(self):
        self.ocr_service = ocr_service
        self.ffmpeg_service = ffmpeg_service
        self.srt_service = srt_service

    def blur_and_add_subtitles(self, req: BlurAndSubtitleRequest) -> Dict[str, Any]:
        """
        Blur original subtitles and add new SRT to video

        Args:
            req: Blur and subtitle request

        Returns:
            Dictionary with output_path and stats
        """
        # Validate input files
        if not os.path.isfile(req.video_path):
            raise FileNotFoundError(f"Video file not found: {req.video_path}")
        if not os.path.isfile(req.srt_path):
            raise FileNotFoundError(f"SRT file not found: {req.srt_path}")

        # Check GPU availability
        gpu_support = self.ffmpeg_service.check_gpu_support()
        use_gpu = req.use_gpu and (
            gpu_support.get("amd_amf", False) or gpu_support.get("nvidia_nvenc", False)
        )

        # Process video with blur and subtitles with GPU acceleration if available
        output_path = self.ffmpeg_service.blur_and_add_subtitles_sequential(
            video_path=req.video_path,
            srt_path=req.srt_path,
            srt_detail=req.srt_detail,
            blur_strength=req.blur_strength,
            blur_expansion_percent=req.blur_expansion_percent,
            output_suffix=req.output_suffix,
            use_gpu=use_gpu,
        )

        return {
            "output_path": output_path,
            "video_path": req.video_path,
            "srt_path": req.srt_path,
            "blur_strength": req.blur_strength,
            "srt_count": len(req.srt_detail) if req.srt_detail else 0,
            "gpu_acceleration": use_gpu,
            "message": "Video processed successfully",
        }

    def blur_video(self, req: BlurRequest) -> Dict[str, Any]:
        """
        Blur regions in video based on SRT detail coordinates

        Args:
            req: Blur request

        Returns:
            Dictionary with output_path and stats
        """
        # Validate input file
        if not os.path.isfile(req.video_path):
            raise FileNotFoundError(f"Video file not found: {req.video_path}")

        # Check GPU availability
        gpu_support = self.ffmpeg_service.check_gpu_support()
        use_gpu = req.use_gpu and (
            gpu_support.get("amd_amf", False) or gpu_support.get("nvidia_nvenc", False)
        )

        # Process video with blur
        output_path = self.ffmpeg_service.blur_and_add_subtitles_sequential(
            video_path=req.video_path,
            srt_path=None,  # No subtitles, only blur
            srt_detail=req.srt_detail,
            blur_strength=req.blur_strength,
            blur_expansion_percent=req.blur_expansion_percent,
            output_suffix=req.output_suffix,
            use_gpu=use_gpu,
        )

        return {
            "output_path": output_path,
            "video_path": req.video_path,
            "blur_strength": req.blur_strength,
            "srt_count": len(req.srt_detail) if req.srt_detail else 0,
            "gpu_acceleration": use_gpu,
            "message": "Video blurred successfully",
        }

    def add_subtitles(self, req: SubtitleRequest) -> Dict[str, Any]:
        """
        Add SRT subtitles to video

        Args:
            req: Subtitle request

        Returns:
            Dictionary with output_path and stats
        """
        # Validate input files
        if not os.path.isfile(req.video_path):
            raise FileNotFoundError(f"Video file not found: {req.video_path}")
        if not os.path.isfile(req.srt_path):
            raise FileNotFoundError(f"SRT file not found: {req.srt_path}")

        # Check GPU availability
        gpu_support = self.ffmpeg_service.check_gpu_support()
        use_gpu = req.use_gpu and (
            gpu_support.get("amd_amf", False) or gpu_support.get("nvidia_nvenc", False)
        )

        # Process video with subtitles only (no blur)
        output_path = self.ffmpeg_service.blur_and_add_subtitles_sequential(
            video_path=req.video_path,
            srt_path=req.srt_path,
            srt_detail=[],  # Empty list, no blur regions
            blur_strength=0,  # No blur
            output_suffix=req.output_suffix,
            use_gpu=use_gpu,
        )

        return {
            "output_path": output_path,
            "video_path": req.video_path,
            "srt_path": req.srt_path,
            "gpu_acceleration": use_gpu,
            "message": "Subtitles added successfully",
        }

    def process_video(
        self,
        req: ExtractRequest,
        progress_callback: Optional[Callable[[float], None]] = None,
        video_path: Optional[str] = None,
        original_filename: Optional[str] = None,
        auto_save_srt: bool = False,
    ) -> ExtractResponse:
        """
        Process video and extract subtitles

        Args:
            req: Extraction request
            progress_callback: Optional callback for progress updates
            video_path: Optional video file path (overrides req.video if provided)
            original_filename: Original filename for auto-save SRT naming
            auto_save_srt: Whether to auto-save SRT to configured output directory

        Returns:
            Extraction response with SRT and stats
        """

        def update_progress(progress: float):
            if progress_callback:
                progress_callback(progress)

        update_progress(0.0)

        # Use provided video_path or fall back to req.video
        effective_video_path = video_path or req.video

        # Validate input
        if not os.path.isfile(effective_video_path):
            raise FileNotFoundError("Video path not found or not a file")

        update_progress(0.05)

        # Try fast path with subtitle streams
        streams = self.ffmpeg_service.probe_subtitle_streams(effective_video_path)
        if req.prefer_subtitle_stream and streams:
            return self._extract_from_stream(
                req, 
                streams, 
                effective_video_path,
                original_filename,
                auto_save_srt
            )

        update_progress(0.15)

        # OCR path
        return self._extract_with_ocr(
            req, 
            streams, 
            update_progress,
            effective_video_path,
            original_filename,
            auto_save_srt
        )

    def process_video_fullfps(
        self,
        req: ExtractRequest,
        progress_callback: Optional[Callable[[float], None]] = None,
        video_path: Optional[str] = None,
        original_filename: Optional[str] = None,
        auto_save_srt: bool = False,
    ) -> ExtractResponse:
        """
        Process video and extract subtitles by running OCR on every sampled frame

        This mode disables the visual hash gating skip (so OCR runs on each sampled
        frame at `target_fps`) and merges consecutive frames with identical text
        into cues based on textual similarity.
        
        Args:
            req: Extraction request
            progress_callback: Optional callback for progress updates
            video_path: Optional video file path (overrides req.video if provided)
            original_filename: Original filename for auto-save SRT naming
            auto_save_srt: Whether to auto-save SRT to configured output directory
        """
        def update_progress(progress: float):
            if progress_callback:
                progress_callback(progress)

        update_progress(0.0)

        # Use provided video_path or fall back to req.video
        effective_video_path = video_path or req.video

        # Validate input
        if not os.path.isfile(effective_video_path):
            raise FileNotFoundError("Video path not found or not a file")

        update_progress(0.05)

        # Try fast path with subtitle streams (honor prefer_subtitle_stream)
        streams = self.ffmpeg_service.probe_subtitle_streams(effective_video_path)
        if req.prefer_subtitle_stream and streams:
            return self._extract_from_stream(
                req, 
                streams,
                effective_video_path,
                original_filename,
                auto_save_srt
            )

        update_progress(0.15)

        # OCR path (force full-fps mode)
        entry = self.ocr_service.get_engine(
            lang=req.lang,
            device=req.device,
            det_model=req.det_model,
            rec_model=req.rec_model,
            use_textline_orientation=req.use_textline_orientation,
        )

        update_progress(0.20)

        cap = cv2.VideoCapture(effective_video_path)
        if not cap.isOpened():
            raise RuntimeError("Cannot open video")

        try:
            return self._process_video_frames(
                cap, 
                req, 
                entry, 
                streams, 
                update_progress, 
                full_fps_mode=True,
                video_path=effective_video_path,
                original_filename=original_filename,
                auto_save_srt=auto_save_srt
            )
        finally:
            cap.release()

    def _extract_from_stream(
        self, 
        req: ExtractRequest, 
        streams: List[dict],
        video_path: str,
        original_filename: Optional[str] = None,
        auto_save_srt: bool = False,
    ) -> ExtractResponse:
        """Extract subtitles from existing stream"""
        from ..core.config import settings
        
        # Determine output path
        if auto_save_srt and original_filename:
            # Auto-save: use configured SRT output directory with original filename
            os.makedirs(settings.SRT_OUTPUT_DIR, exist_ok=True)
            base_name = os.path.splitext(original_filename)[0]
            out_path = os.path.join(settings.SRT_OUTPUT_DIR, f"{base_name}.srt")
        else:
            # Default: save in same directory as video with .srt extension
            out_path = video_path + ".srt"

        try:
            self.ffmpeg_service.extract_stream_subtitle_to_srt(
                video_path, out_path, stream_index=0
            )
            with open(out_path, "r", encoding="utf-8", errors="replace") as f:
                srt_text = f.read()

            return ExtractResponse(
                srt=srt_text,
                srt_output_path=out_path if auto_save_srt else None,
                stats={
                    "mode": "subtitle_stream",
                    "streams": streams,
                },
            )
        except Exception as e:
            raise RuntimeError(f"Stream subtitle extract failed: {e}")

    def _extract_with_ocr(
        self,
        req: ExtractRequest,
        streams: List[dict],
        update_progress: Callable[[float], None],
        video_path: str,
        original_filename: Optional[str] = None,
        auto_save_srt: bool = False,
    ) -> ExtractResponse:
        """Extract subtitles using OCR"""

        # Get OCR engine
        entry = self.ocr_service.get_engine(
            lang=req.lang,
            device=req.device,
            det_model=req.det_model,
            rec_model=req.rec_model,
            use_textline_orientation=req.use_textline_orientation,
        )

        update_progress(0.20)

        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError("Cannot open video")

        try:
            return self._process_video_frames(
                cap, 
                req, 
                entry, 
                streams, 
                update_progress,
                video_path=video_path,
                original_filename=original_filename,
                auto_save_srt=auto_save_srt
            )
        finally:
            cap.release()

    def _process_video_frames(
        self,
        cap: cv2.VideoCapture,
        req: ExtractRequest,
        entry,
        streams: List[dict],
        update_progress: Callable[[float], None],
        full_fps_mode: bool = False,
        video_path: Optional[str] = None,
        original_filename: Optional[str] = None,
        auto_save_srt: bool = False,
    ) -> ExtractResponse:
        """Process video frames and extract subtitles"""
        from ..core.config import settings
        
        print("Current target FPS:", req.target_fps)
        # Get video properties
        src_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        # Read first frame for letterbox detection
        ok, frame0 = cap.read()
        if not ok or frame0 is None:
            raise RuntimeError("Failed to read video frames")

        H, W = frame0.shape[:2]
        active_top, active_bottom = detect_active_vertical_region(frame0)

        # Auto-detect subtitle region if using default bottom_start
        effective_bottom_start = req.bottom_start
        if req.bottom_start == 0.0:
            # Try to auto-detect subtitle region from first frame
            try:
                detected_bottom_start = detect_subtitle_region(frame0)
                # Only use detected value if it's reasonable (not too close to top or bottom)
                if 0.0 <= detected_bottom_start <= 0.9:
                    effective_bottom_start = detected_bottom_start
            except Exception:
                # Fallback to full frame if detection fails
                effective_bottom_start = 0.0

        # Reset to start
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Calculate frame stepping
        if src_fps > 0:
            step = max(1, int(round(src_fps / req.target_fps)))
            frame_interval = step / src_fps
        else:
            step = 1
            frame_interval = 1.0 / req.target_fps

        # Initialize stats
        t0 = time.time()
        stats = {
            "frames_seen": 0,
            "frames_sampled": 0,
            "frames_hashed_skipped": 0,
            "frames_ocr": 0,
            "t_decode": 0.0,
            "t_ocr": 0.0,
        }

        # Process frames
        cues_raw = self._ocr_loop(
            cap,
            req,
            entry,
            step,
            src_fps,
            frame_interval,
            active_top,
            active_bottom,
            total_frames,
            stats,
            update_progress,
            effective_bottom_start,
            full_fps_mode=full_fps_mode,
        )

        update_progress(0.92)

        # Finalize cues
        cues = self.srt_service.merge_and_filter_cues(
            cues_raw,
            min_duration_ms=req.min_duration_ms,
            merge_gap_ms=req.merge_gap_ms,
            sim_thr=req.sim_thr,
        )

        update_progress(0.95)

        # Generate SRT
        srt_text = self.srt_service.cues_to_srt(cues)
        srt_details = self.srt_service.generate_srt_details(cues)

        # Determine output path for auto-save
        srt_output_path = None
        if auto_save_srt and original_filename:
            # Auto-save: use configured SRT output directory with original filename
            os.makedirs(settings.SRT_OUTPUT_DIR, exist_ok=True)
            base_name = os.path.splitext(original_filename)[0]
            srt_output_path = os.path.join(settings.SRT_OUTPUT_DIR, f"{base_name}.srt")
            with open(srt_output_path, "w", encoding="utf-8") as f:
                f.write(srt_text)

        update_progress(0.98)

        # Build response
        total_ms = int(round((time.time() - t0) * 1000))
        response_stats = {
            "mode": "ocr",
            "frames_seen": stats["frames_seen"],
            "frames_sampled": stats["frames_sampled"],
            "frames_hashed_skipped": stats["frames_hashed_skipped"],
            "frames_ocr": stats["frames_ocr"],
            "cues": len(cues),
            "timing_ms": {
                "total": total_ms,
                "decode": int(round(stats["t_decode"] * 1000)),
                "ocr": int(round(stats["t_ocr"] * 1000)),
            },
            "video": {
                "width": W,
                "height": H,
                "src_fps": src_fps,
                "active_top": active_top,
                "active_bottom": active_bottom,
            },
            "subtitle_streams_found": streams,
        }

        update_progress(1.0)

        return ExtractResponse(
            srt=srt_text, 
            srt_detail=srt_details, 
            stats=response_stats,
            srt_output_path=srt_output_path
        )

    def _ocr_loop(
        self,
        cap: cv2.VideoCapture,
        req: ExtractRequest,
        entry,
        step: int,
        src_fps: float,
        frame_interval: float,
        active_top: int,
        active_bottom: int,
        total_frames: int,
        stats: dict,
        update_progress: Callable[[float], None],
        bottom_start: float = None,
        full_fps_mode: bool = False,
    ) -> List[Tuple[float, float, str, List[Tuple[float, float, float, float]]]]:
        """Main OCR processing loop"""
        
        # Use provided bottom_start or fallback to request's bottom_start
        if bottom_start is None:
            bottom_start = req.bottom_start

        use_batch_ocr = req.device.startswith("gpu") and settings.BATCH_OCR_SIZE > 1
        ocr_batch_buffer: List[Tuple[float, np.ndarray]] = []

        # Segmenter state
        current: Optional[CueDraft] = None
        pending_text: Optional[str] = None
        pending_first_time: float = 0.0
        pending_count: int = 0
        empty_pending_count: int = 0
        last_time: float = 0.0
        cues_raw: List[
            Tuple[float, float, str, List[Tuple[float, float, float, float]]]
        ] = []

        prev_hash = None
        prev_roi = None
        frame_idx = 0

        def accept_text_at(
            t: float, text: str, bbox: List[Tuple[float, float, float, float]] = None
        ):
            nonlocal current
            if current is None:
                current = CueDraft(start=t, last=t, text_votes=Counter(), bbox_list=[])
            current.last = t
            # Normalize text by stripping quotes before voting
            # This ensures "text" and text and 'text' are treated as the same
            normalized_text = strip_quotes(text)
            current.text_votes[normalized_text] += 1
            if bbox:
                current.bbox_list.extend(bbox)

        def close_current(end_t: float):
            nonlocal current
            if current is None:
                return
            s, e, text, bbox_list = self.srt_service.finalize_cue(current)
            e = max(e, end_t)
            cues_raw.append((s, e, text, bbox_list))
            current = None

        def process_subtitle_frame(
            ts: float, sub: str, bbox: List[Tuple[float, float, float, float]] = None
        ):
            nonlocal current, pending_text, pending_first_time, pending_count
            nonlocal empty_pending_count, last_time

            if not sub:
                empty_pending_count += 1
                if empty_pending_count >= req.empty_debounce_frames:
                    close_current(ts)
                    # Reset pending state properly
                    pending_text = None
                    pending_count = 0
                    empty_pending_count = 0  # Reset counter after closing
                last_time = ts
                return

            empty_pending_count = 0

            if current is None:
                accept_text_at(ts, sub, bbox)
                pending_text = None
                pending_count = 0
                last_time = ts
                return

            cur_best = (
                current.text_votes.most_common(1)[0][0] if current.text_votes else ""
            )
            if similarity(sub, cur_best) >= req.sim_thr:
                accept_text_at(ts, sub, bbox)
                pending_text = None
                pending_count = 0
            else:
                if pending_text is None or similarity(sub, pending_text) < req.sim_thr:
                    pending_text = sub
                    pending_first_time = ts
                    pending_count = 1
                else:
                    pending_count += 1

                if pending_count >= req.debounce_frames:
                    close_current(pending_first_time)
                    accept_text_at(pending_first_time, pending_text, bbox)
                    pending_text = None
                    pending_count = 0

            last_time = ts

        def process_ocr_batch():
            nonlocal ocr_batch_buffer, stats
            if not ocr_batch_buffer:
                return []

            rois = [roi for _, roi in ocr_batch_buffer]
            timestamps = [ts for ts, _ in ocr_batch_buffer]

            t2 = time.time()
            if use_batch_ocr and len(rois) > 1:
                batch_results = self.ocr_service.run_ocr_batch(entry, rois)
            else:
                batch_results = [self.ocr_service.run_ocr(entry, roi) for roi in rois]
            stats["t_ocr"] += time.time() - t2
            stats["frames_ocr"] += len(rois)

            results = list(zip(timestamps, batch_results))
            ocr_batch_buffer = []
            return results

        # Main frame loop
        while True:
            t1 = time.time()
            ok, frame = cap.read()
            stats["t_decode"] += time.time() - t1

            if not ok or frame is None:
                break

            stats["frames_seen"] += 1

            # Progress update
            if total_frames > 0 and stats["frames_seen"] % 100 == 0:
                progress = 0.20 + (0.70 * stats["frames_seen"] / total_frames)
                update_progress(min(progress, 0.90))

            # Frame sampling
            do_sample = src_fps <= 0 or (frame_idx % step == 0)

            if do_sample:
                stats["frames_sampled"] += 1

                # Calculate timestamp
                if src_fps > 0:
                    t_sec = frame_idx / src_fps
                else:
                    t_sec = stats["frames_sampled"] * (1.0 / req.target_fps)

                # Extract and process ROI
                roi, transform = self._extract_roi(
                    frame,
                    active_top,
                    active_bottom,
                    req.bottom_start,
                    req.max_width,
                    req.enhance,
                )

                # Hash gating - Enhanced detection for subtitle changes
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                hcur = ahash(gray, size=8)

                # Skip frame if:
                # 1. Hash is similar (simple optimization)
                # 2. BUT don't skip if there's actual content change (text appeared/changed)
                # 3. OR text motion detected (new subtitle transition)
                # 4. OR text presence changed (empty→text or text→empty)
                # 5. OR intensity spike (brightness changes)
                skip_by_hash = (
                    prev_hash is not None
                    and hamming64(prev_hash, hcur) <= req.hash_dist_thr
                )
                
                # Check if content actually changed despite similar hash
                content_changed = False
                text_moved = False
                presence_changed = False
                intensity_spiked = False
                
                if skip_by_hash and prev_roi is not None:
                    # Layer 2: Content analysis (edge detection)
                    content_changed = detect_roi_content_change(
                        prev_roi, roi, change_thr=req.content_change_thr
                    )
                    
                    # Layer 3: Motion detection (optical flow)
                    text_moved = detect_text_motion(prev_roi, roi, motion_thr=req.text_motion_thr)
                    
                    # Layer 4: Text presence change (empty→text or text→empty or long→short)
                    presence_changed = detect_text_presence_change(
                        prev_roi, roi, presence_thr=req.text_presence_thr
                    )
                    
                    # Layer 5: Intensity spike (dark→bright or bright→dark)
                    intensity_spiked = detect_intensity_spike(
                        prev_roi, roi, spike_thr=req.intensity_spike_thr
                    )

                # In full-fps mode we intentionally do not skip OCR based on visual hashing
                if full_fps_mode:
                    should_skip = False
                else:
                    # Skip only if all checks pass (no change detected)
                    should_skip = (
                        skip_by_hash
                        and not content_changed
                        and not text_moved
                        and not presence_changed
                        and not intensity_spiked
                    )

                if should_skip:
                    stats["frames_hashed_skipped"] += 1
                    if current is not None:
                        current.last = t_sec
                    last_time = t_sec
                    prev_roi = roi  # Update for next comparison
                    frame_idx += 1
                    continue

                prev_hash = hcur
                prev_roi = roi

                # OCR processing
                if use_batch_ocr:
                    ocr_batch_buffer.append((t_sec, roi))
                    if len(ocr_batch_buffer) >= settings.BATCH_OCR_SIZE:
                        for batch_ts, (texts, scores, polys) in process_ocr_batch():
                            # Extract bounding boxes from polygons
                            bbox_list = self._extract_bboxes_from_polys(polys)
                            bbox_list = self._map_bbox_to_frame(bbox_list, transform)
                            subtitle = self.ocr_service.assemble_subtitle_text(
                                texts, scores, polys, req.conf_min
                            )
                            subtitle = normalize_text(subtitle)
                            process_subtitle_frame(batch_ts, subtitle, bbox_list)
                else:
                    t2 = time.time()
                    texts, scores, polys = self.ocr_service.run_ocr(entry, roi)
                    stats["t_ocr"] += time.time() - t2
                    stats["frames_ocr"] += 1

                    # Extract bounding boxes from polygons
                    bbox_list = self._extract_bboxes_from_polys(polys)
                    bbox_list = self._map_bbox_to_frame(bbox_list, transform)
                    subtitle = self.ocr_service.assemble_subtitle_text(
                        texts, scores, polys, req.conf_min
                    )
                    subtitle = normalize_text(subtitle)
                    process_subtitle_frame(t_sec, subtitle, bbox_list)

            frame_idx += 1

        # Process remaining batch
        if ocr_batch_buffer:
            for batch_ts, (texts, scores, polys) in process_ocr_batch():
                # Extract bounding boxes from polygons
                bbox_list = self._extract_bboxes_from_polys(polys)
                bbox_list = self._map_bbox_to_frame(bbox_list, transform)
                subtitle = self.ocr_service.assemble_subtitle_text(
                    texts, scores, polys, req.conf_min
                )
                subtitle = normalize_text(subtitle)
                process_subtitle_frame(batch_ts, subtitle, bbox_list)

        # Close final cue
        if current is not None:
            close_current(last_time)

        return cues_raw

    def _extract_roi(
        self,
        frame: np.ndarray,
        active_top: int,
        active_bottom: int,
        bottom_start: float,
        max_width: int,
        do_enhance: bool
    ):
        """
        Extract ROI + return transform info to map bbox back to frame space
        """

        # ---- Active crop ----
        active = frame[active_top:active_bottom, :, :]

        # ---- Bottom crop ----
        active_h = active.shape[0]
        y0 = int(active_h * bottom_start)
        y0 = max(0, min(y0, active_h - 1))

        roi = active[y0:, :, :]

        # ---- Resize ----
        scale = 1.0
        if roi.shape[1] > max_width:
            scale = max_width / float(roi.shape[1])
            new_h = int(round(roi.shape[0] * scale))
            roi = cv2.resize(
                roi,
                (max_width, new_h),
                interpolation=cv2.INTER_AREA
            )

        # ---- Enhance ----
        if do_enhance:
            roi = enhance_roi(roi)

        transform = {
            "active_top": active_top,
            "roi_y_offset": y0,
            "scale": scale
        }

        return roi, transform

    def _extract_bboxes_from_polys(
        self, polys: Optional[np.ndarray]
    ) -> List[Tuple[float, float, float, float]]:
        """
        Extract bounding boxes from polygon coordinates

        Args:
            polys: Polygon coordinates from OCR (Nx4x2 array or similar)

        Returns:
            List of (x1, y1, x2, y2) tuples
        """
        if polys is None:
            return []

        bbox_list = []
        try:
            # Convert to numpy array if not already
            if not isinstance(polys, np.ndarray):
                polys = np.array(polys)

            # Handle single polygon or multiple polygons
            if polys.ndim == 2:
                # Single polygon: shape (4, 2)
                polys = polys.reshape(1, -1, 2)
            elif polys.ndim == 3:
                # Multiple polygons: shape (N, 4, 2)
                pass
            else:
                return []

            # Extract bbox from each polygon
            for poly in polys:
                if len(poly) >= 2:
                    xs = poly[:, 0]
                    ys = poly[:, 1]
                    x1, x2 = float(np.min(xs)), float(np.max(xs))
                    y1, y2 = float(np.min(ys)), float(np.max(ys))
                    bbox_list.append((x1, y1, x2, y2))
        except (ValueError, IndexError, TypeError):
            # Return empty list if there's any parsing error
            return []

        return bbox_list

    def _map_bbox_to_frame(self, bbox_list, transform):
        """
        Convert bbox from ROI space -> original frame space
        """
        if not bbox_list:
            return bbox_list

        mapped = []

        scale = transform["scale"]
        active_top = transform["active_top"]
        roi_y_offset = transform["roi_y_offset"]

        inv_scale = 1.0 / scale if scale != 0 else 1.0

        for x1, y1, x2, y2 in bbox_list:

            # Undo resize
            x1 *= inv_scale
            x2 *= inv_scale
            y1 *= inv_scale
            y2 *= inv_scale

            # Undo bottom crop
            y1 += roi_y_offset
            y2 += roi_y_offset

            # Undo active crop
            y1 += active_top
            y2 += active_top

            mapped.append((x1, y1, x2, y2))

        return mapped

# Singleton instance
video_processor = VideoProcessor()

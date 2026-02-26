"""FFmpeg service for subtitle stream extraction"""

import json
import subprocess
import os
from typing import List, Tuple, Dict
from pathlib import Path


class FfmpegService:
    """Service for FFmpeg operations"""

    @staticmethod
    def check_gpu_support() -> Dict[str, bool]:
        """
        Check available GPU acceleration

        Returns:
            Dictionary with GPU support status
        """
        gpu_support = {
            "amd_amf": False,
            "nvidia_nvenc": False,
            "intel_qsv": False,
            "vaapi": False,
        }

        try:
            # Check for encoders
            cmd = ["ffmpeg", "-codecs", "-hide_banner"]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            output = p.stdout.lower() + p.stderr.lower()

            if "h264_amf" in output or "hevc_amf" in output:
                gpu_support["amd_amf"] = True
            if "h264_nvenc" in output or "hevc_nvenc" in output:
                gpu_support["nvidia_nvenc"] = True
            if "h264_qsv" in output or "hevc_qsv" in output:
                gpu_support["intel_qsv"] = True
            if "scale_vaapi" in output:
                gpu_support["vaapi"] = True

        except Exception:
            pass

        return gpu_support

    @staticmethod
    def probe_subtitle_streams(video_path: str) -> List[dict]:
        """
        Detect subtitle streams in video file

        Args:
            video_path: Path to video file

        Returns:
            List of subtitle stream metadata
        """
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "s",
            "-show_entries",
            "stream=index,codec_name:stream_tags=language",
            "-of",
            "json",
            video_path,
        ]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if p.returncode != 0:
                return []
            data = json.loads(p.stdout or "{}")
            return data.get("streams", []) or []
        except Exception:
            return []

    @staticmethod
    def extract_stream_subtitle_to_srt(
        video_path: str, out_srt_path: str, stream_index: int = 0
    ) -> None:
        """
        Extract subtitle stream and convert to SRT

        Args:
            video_path: Path to video file
            out_srt_path: Output SRT file path
            stream_index: Subtitle stream index

        Raises:
            RuntimeError: If extraction fails
        """
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            video_path,
            "-map",
            f"0:s:{stream_index}",
            "-c:s",
            "srt",
            out_srt_path,
        ]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(p.stderr or "ffmpeg subtitle extract failed")

    @staticmethod
    def get_video_dimensions(video_path: str) -> Tuple[int, int]:
        """
        Get video width and height

        Args:
            video_path: Path to video file

        Returns:
            Tuple of (width, height)

        Raises:
            RuntimeError: If probe fails
        """
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            video_path,
        ]
        try:
            p = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8",
                errors="ignore",
            )
            if p.returncode != 0:
                raise RuntimeError("Failed to get video dimensions")
            width, height = map(int, p.stdout.strip().split(","))
            return width, height
        except Exception as e:
            raise RuntimeError(f"Failed to probe video: {e}")

    @staticmethod
    def _parse_srt_time(srt_time: str) -> Tuple[float, float]:
        """
        Parse SRT time format (HH:MM:SS,mmm --> HH:MM:SS,mmm) to seconds

        Args:
            srt_time: SRT time string like "00:00:01,500 --> 00:00:05,000"

        Returns:
            Tuple of (start_time_sec, end_time_sec)
        """
        try:
            parts = srt_time.split("-->")
            start_str = parts[0].strip()
            end_str = parts[1].strip()

            def time_to_seconds(time_str: str) -> float:
                # Format: HH:MM:SS,mmm
                time_str = time_str.replace(",", ".")
                parts = time_str.split(":")
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds

            return time_to_seconds(start_str), time_to_seconds(end_str)
        except Exception:
            return 0.0, float("inf")

    @staticmethod
    def blur_and_add_subtitles_sequential(
        video_path: str,
        srt_path: str,
        srt_detail: list,
        blur_strength: int = 25,
        blur_expansion_percent: int = 0,
        output_suffix: str = "vnsrt",
        use_gpu: bool = True,
    ) -> str:
        """
        Blur original subtitles and/or add new SRT with precise timing using segment-based approach
        Splits video into segments (before blur, blur region, after blur) and reconstructes

        Args:
            video_path: Path to input video
            srt_path: Path to SRT file to add (can be None for blur only)
            srt_detail: List of SRT detail objects with coordinates and srt_time
            blur_strength: Blur strength (1-100)
            blur_expansion_percent: Blur region expansion percentage (0-10%)
            output_suffix: Output file suffix
            use_gpu: Enable GPU acceleration if available

        Returns:
            Path to output video

        Raises:
            RuntimeError: If processing fails
        """
        if srt_path is not None:
            if not Path(srt_path).exists():
                raise RuntimeError(f"SRT file not found: {srt_path}")

        srt_path_fixed = None
        if srt_path:
            srt_path_fixed = str(Path(srt_path).resolve())
            srt_path_fixed = srt_path_fixed.replace("\\", "/")

        # Get video dimensions
        width, height = FfmpegService.get_video_dimensions(video_path)

        # Generate output path
        base_path = str(video_path)
        path_obj = Path(base_path)
        output_path = (
            path_obj.parent / f"{path_obj.stem}_{output_suffix}{path_obj.suffix}"
        )

        # Validate blur strength
        blur_radius = max(1, min(13, int(blur_strength)))

        # Build filter chain with timing-aware blur processing
        # Use segment-based approach: blur regions are applied only during specified time ranges
        filter_chain, final_label = FfmpegService._build_segment_blur_filter_chain(
            srt_detail, width, height, blur_radius, srt_path_fixed, blur_expansion_percent
        )

        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
        ]

        # Add hardware decoding if available
        if use_gpu:
            gpu_support = FfmpegService.check_gpu_support()
            if gpu_support["amd_amf"] or gpu_support["vaapi"]:
                # Use hardware decoding for faster processing
                cmd.extend(["-hwaccel", "auto"])

        cmd.extend(
            [
                "-i",
                video_path,
                "-filter_complex",
                filter_chain,
            ]
        )

        cmd.extend(["-map", f"[{final_label}]", "-map", "0:a?"])

        # Add encoding codec based on GPU availability
        if use_gpu:
            gpu_support = FfmpegService.check_gpu_support()
            if gpu_support["amd_amf"]:
                # Use AMD AMF for encoding (H.264)
                cmd.extend(
                    [
                        "-c:v",
                        "h264_amf",
                        "-quality",
                        "balanced",  # balanced, speed, quality
                    ]
                )
            elif gpu_support["nvidia_nvenc"]:
                cmd.extend(
                    [
                        "-c:v",
                        "h264_nvenc",
                        "-preset",
                        "fast",  # fast, medium, slow
                    ]
                )
            else:
                # Fallback to CPU with optimizations
                cmd.extend(
                    [
                        "-c:v",
                        "libx264",
                        "-preset",
                        "fast",
                    ]
                )
        else:
            cmd.extend(
                [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                ]
            )

        # Copy audio stream
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])

        cmd.append(str(output_path))

        try:
            p = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            if p.returncode != 0:
                raise RuntimeError(p.stderr or "ffmpeg processing failed")
            return str(output_path)
        except Exception as e:
            raise RuntimeError(f"Failed to process video: {e}")

    @staticmethod
    def _build_segment_blur_filter_chain(
        srt_detail: list,
        video_width: int,
        video_height: int,
        blur_radius: int,
        srt_path: str,
        blur_expansion_percent: int = 0,
    ):
        """
        Build filter chain that:
        - Crops each region, blurs it, and overlays back at (x1,y1)
        - Expands blur region by blur_expansion_percent before clamping to video boundaries
        - Uses enable='between(t,START,END)' to restrict blur to srt_time
        - Uses split=2 per-region so both outputs are consumed (no unconnected outputs)
        - Always returns (filter_chain, final_label)
        """
        # Case: no regions
        if not srt_detail:
            if srt_path:
                return (
                    f"[0:v]format=yuv420p,subtitles=filename='{srt_path}':force_style='FontName=Arial,FontSize=20'[vout]",
                    "vout",
                )
            else:
                return ("[0:v]null[vout]", "vout")

        parts = []
        # Ensure initial pixel format compatible
        parts.append("[0:v]format=yuv420p[base0]")
        current_label = "base0"

        # sane blur radii
        luma = max(1, min(int(blur_radius), 13))
        chroma = min(luma, 12)

        # Process all regions (FFmpeg can handle ~50+ filters in a chain with enable switches)
        # The 'enable' parameter ensures blur is only applied during specific time ranges,
        # so excessive filter complexity is avoided
        max_regions = len(srt_detail)

        for idx, detail in enumerate(srt_detail):
            try:
                x1 = int(detail.get("x1", 0))
                y1 = int(detail.get("y1", 0))
                x2 = int(detail.get("x2", 0))
                y2 = int(detail.get("y2", 0))
                srt_time = detail.get("srt_time", "")

                start_time, end_time = FfmpegService._parse_srt_time(srt_time)
                start_time = round(start_time, 3)
                end_time = round(end_time, 3)
                
                # clamp coords first
                x1 = max(0, min(x1, video_width - 2))
                y1 = max(0, min(y1, video_height - 2))
                x2 = max(x1 + 1, min(x2, video_width))
                y2 = max(y1 + 1, min(y2, video_height))

                box_w = x2 - x1
                box_h = y2 - y1

                # Apply expansion if specified
                if blur_expansion_percent > 0:
                    # Calculate expanded dimensions
                    expanded_w = int(box_w * (1 + blur_expansion_percent / 100))
                    expanded_h = int(box_h * (1 + blur_expansion_percent / 100))
                    
                    # Calculate center of original box
                    center_x = x1 + box_w / 2
                    center_y = y1 + box_h / 2
                    
                    # Calculate new coordinates centered on original box
                    x1_expanded = int(center_x - expanded_w / 2)
                    y1_expanded = int(center_y - expanded_h / 2)
                    x2_expanded = x1_expanded + expanded_w
                    y2_expanded = y1_expanded + expanded_h
                    
                    # Clamp expanded coordinates to video boundaries
                    x1 = max(0, min(x1_expanded, video_width - 2))
                    y1 = max(0, min(y1_expanded, video_height - 2))
                    x2 = max(x1 + 1, min(x2_expanded, video_width))
                    y2 = max(y1 + 1, min(y2_expanded, video_height))

                box_w = x2 - x1
                box_h = y2 - y1

                # Use split so we can both keep the base and crop from it
                keep_label = f"keep{idx}"
                crop_src_label = f"cropsrc{idx}"
                parts.append(
                    f"[{current_label}]split=2[{keep_label}][{crop_src_label}]"
                )

                # Crop from the crop source
                parts.append(
                    f"[{crop_src_label}]crop=w={box_w}:h={box_h}:x={x1}:y={y1}[crop{idx}]"
                )

                # Blur the crop
                parts.append(
                    f"[crop{idx}]boxblur=luma_radius={luma}:chroma_radius={chroma}[blur{idx}]"
                )

                # Overlay blurred crop back onto the kept base at x1,y1 with enable timing
                next_label = f"v{idx}"
                # overlay uses first input (base) then second input (overlay image)
                # note: overlay's x and y are absolute on base frame
                parts.append(
                    f"[{keep_label}][blur{idx}]overlay=x={x1}:y={y1}:enable='between(t,{start_time},{end_time})'[{next_label}]"
                )

                # Advance current_label for next iteration
                current_label = next_label

            except Exception:
                # skip any malformed region without failing whole graph
                continue

        # Attach subtitles if provided
        if srt_path:
            parts.append(
                f"[{current_label}]subtitles=filename='{srt_path}':force_style='FontName=Arial,FontSize=20'[vout]"
            )
            final_label = "vout"
        else:
            final_label = current_label

        return ";".join(parts), final_label

# Singleton instance
ffmpeg_service = FfmpegService()

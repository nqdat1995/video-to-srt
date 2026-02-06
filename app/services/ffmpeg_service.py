"""FFmpeg service for subtitle stream extraction"""

import json
import subprocess
from typing import List


class FfmpegService:
   """Service for FFmpeg operations"""

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
           "ffprobe", "-v", "error",
           "-select_streams", "s",
           "-show_entries", "stream=index,codec_name:stream_tags=language",
           "-of", "json",
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
       video_path: str,
       out_srt_path: str,
       stream_index: int = 0
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
           "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-i", video_path,
           "-map", f"0:s:{stream_index}",
           "-c:s", "srt",
           out_srt_path,
       ]
       p = subprocess.run(cmd, capture_output=True, text=True)
       if p.returncode != 0:
           raise RuntimeError(p.stderr or "ffmpeg subtitle extract failed")


# Singleton instance
ffmpeg_service = FfmpegService()

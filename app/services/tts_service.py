"""TTS (Text-to-Speech) Service Module

Handles audio synthesis from SRT subtitles, including:
- WebSocket communication with TTS API
- Audio file download and management
- Audio merging and timeline synchronization
- Base64 encoding for API responses
"""

import json
import os
import re
import subprocess
import threading
import uuid
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Tuple
from pathlib import Path
import base64

try:
    import websocket
except ImportError:
    websocket = None


@dataclass
class TTSMessage:
    """TTS API message structure"""
    task_id: str
    message_id: str
    namespace: str
    event: str
    status_code: int
    status_text: str
    payload: str


class TTSError(Exception):
    """Base exception for TTS operations"""
    pass


class RetriableConnectionError(TTSError):
    """WebSocket connection error that can be retried"""
    pass


class TTSService:
    """Service for TTS operations"""

    def __init__(self, tts_voice: str = "default", api_key: str = None, api_token: str = None):
        """
        Initialize TTS service

        Args:
            tts_voice: Voice identifier for TTS (e.g., "BV074_streaming")
            api_key: API key for TTS service (from config)
            api_token: API token for authentication (from config)
        """
        self.tts_voice = tts_voice
        self.api_key = api_key or "ddjeqjLGMn"  # Default key
        self.api_token = api_token or os.getenv("TTS_API_TOKEN", "")
        
        # State variables
        self._last_message: Optional[TTSMessage] = None
        self._current_wav_filename: Optional[str] = None
        self._tts_error: Optional[Exception] = None
        self._current_index_offset: int = 0

    def _deserialize_message(self, text: str) -> Optional[TTSMessage]:
        """Deserialize JSON message from TTS API"""
        try:
            obj = json.loads(text)
            return TTSMessage(
                task_id=str(obj.get("task_id", "")),
                message_id=str(obj.get("message_id", "")),
                namespace=str(obj.get("namespace", "")),
                event=str(obj.get("event", "")),
                status_code=int(obj.get("status_code", 0) or 0),
                status_text=str(obj.get("status_text", "")),
                payload=obj.get("payload", "") if isinstance(obj.get("payload", ""), str)
                        else json.dumps(obj.get("payload"))
            )
        except Exception:
            return None

    def create_ws_payload(self, subtitle_dict: List[Dict]) -> Dict:
        """
        Create WebSocket payload for TTS request

        Args:
            subtitle_dict: List of subtitle dictionaries with 'content' key

        Returns:
            Payload dictionary for TTS API
        """
        # Sort by sequence number
        sorted_data = sorted(subtitle_dict, key=lambda x: x.get("sequence", 0))

        # Extract content list
        contents = [item.get("content", "") for item in sorted_data]

        # Inner payload with audio configuration
        inner_payload = {
            "audio_config": {
                "bit_rate": 64000,
                "enable_split": False,
                "enable_timestamp": True,
                "format": "wave",
                "sample_rate": 24000,
                "speech_rate": 0
            },
            "speaker": self.tts_voice,
            "texts": contents
        }

        # Serialize to JSON string
        inner_payload_str = json.dumps(inner_payload, ensure_ascii=False)

        # Outer payload
        payload = {
            "appkey": self.api_key,
            "event": "StartTask",
            "namespace": "TTS",
            "payload": inner_payload_str,
            "token": self.api_token,
            "version": "sdk_v1"
        }

        return payload

    def _make_on_message(self, project_path: str):
        """Factory function to create on_message handler"""
        def on_message(ws, message):
            if isinstance(message, bytes):
                # Handle binary audio data
                if self._current_wav_filename:
                    wav_path = os.path.join(project_path, "textReading", self._current_wav_filename)
                    os.makedirs(os.path.dirname(wav_path), exist_ok=True)
                    with open(wav_path, "wb") as f:
                        f.write(message)

            else:
                # Text message
                msg_obj = self._deserialize_message(message)
                if msg_obj is None:
                    return

                # Cache last message
                self._last_message = msg_obj

                # Handle TTSResponse event
                if msg_obj.event == "TTSResponse":
                    try:
                        payload = json.loads(msg_obj.payload)
                        index = payload.get("index", 0)
                        self._current_wav_filename = f"{index + 1}.wav"
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Handle TaskStarted event
                if msg_obj.event == "TaskStarted":
                    finish_payload = {
                        "event": "FinishTask",
                        "namespace": "TTS",
                        "appkey": self.api_key,
                        "token": self.api_token,
                        "version": "sdk_v1",
                        "task_id": msg_obj.task_id,
                        "payload": None
                    }
                    ws.send(json.dumps(finish_payload))

                # Handle TaskFinished event
                if msg_obj.event == "TaskFinished":
                    ws.close()

        return on_message

    def _make_on_error(self):
        """Factory function to create on_error handler"""
        def on_error(ws, error):
            error_message = str(error)
            print(f"[TTS] WebSocket Error: {error_message}")  # Log the error
            retriable_patterns = [
                r"ConnectionRefusedError",
                r"ConnectionResetError",
                r"Connection to remote host was lost",
                r"\[Errno 104\] Connection reset by peer",
                r"\[Errno 111\] Connection refused",
                r"\[Errno 8\] nodename nor servname provided",
                r"ConnectionAbortedError",
            ]

            is_retriable = any(re.search(pattern, error_message) for pattern in retriable_patterns)

            if is_retriable:
                self._tts_error = RetriableConnectionError(f"Retriable connection error:\n{error}")
            else:
                self._tts_error = TTSError(f"WebSocket error:\n{error}")

            ws.close()

        return on_error

    def _make_on_close(self):
        """Factory function to create on_close handler"""
        def on_close(ws, close_status, close_msg):
            print(f"[TTS] WebSocket closed - Status: {close_status}, Message: {close_msg}")

        return on_close

    def download_wav_from_srt(self, project_path: str, subtitle_dict: List[Dict],
                             batch_size: int = 1000, max_retries: int = 3) -> bool:
        """
        Download audio files from TTS API based on SRT content

        Args:
            project_path: Path to save audio files
            subtitle_dict: List of subtitle dictionaries
            batch_size: Size of each TTS batch
            max_retries: Maximum retry attempts for connection errors

        Returns:
            True if successful, False otherwise

        Raises:
            TTSError: If non-retriable error occurs
        """
        if not websocket:
            raise TTSError("websocket library not installed. Install with: pip install websocket-client")

        # Reset state
        self._tts_error = None
        self._last_message = None
        self._current_wav_filename = None
        self._current_index_offset = 0

        try:
            url = "wss://sami-normal-sg.capcutapi.com/internal/api/v1/ws"

            ws_headers = [
                "Host: sami-normal-sg.capcutapi.com",
                "Connection: Upgrade",
                "Pragma: no-cache",
                "Cache-Control: no-cache",
                "Upgrade: websocket",
                "Origin: null",
                "Sec-WebSocket-Version: 13",
                "User-Agent: Cronet/TTNetVersion",
                "Accept-Encoding: gzip, deflate",
            ]

            audios_path = os.path.join(project_path, "textReading")
            os.makedirs(audios_path, exist_ok=True)

            # Clear existing audio files
            for f in os.listdir(audios_path):
                if f.lower().endswith(".wav"):
                    os.remove(os.path.join(audios_path, f))

            # Process in batches
            num_subtitles = len(subtitle_dict)
            retry_count = 0

            for batch_start in range(0, num_subtitles, batch_size):
                batch_end = min(batch_start + batch_size, num_subtitles)
                batch_data = subtitle_dict[batch_start:batch_end]

                self._current_index_offset = batch_start

                retry_attempt = 0
                while retry_attempt < max_retries:
                    try:
                        # Create WebSocket connection
                        ws = websocket.WebSocketApp(
                            url,
                            header=ws_headers,
                            on_open=self._make_on_open(batch_data),
                            on_message=self._make_on_message(project_path),
                            on_error=self._make_on_error(),
                            on_close=self._make_on_close()
                        )

                        ws.run_forever()

                        # Check for errors
                        if self._tts_error:
                            if isinstance(self._tts_error, RetriableConnectionError):
                                retry_attempt += 1
                                if retry_attempt >= max_retries:
                                    raise self._tts_error
                                continue
                            else:
                                raise self._tts_error

                        break  # Success, move to next batch

                    except RetriableConnectionError:
                        retry_attempt += 1
                        if retry_attempt >= max_retries:
                            raise

            return True

        except Exception as e:
            raise TTSError(f"Failed to download audio: {str(e)}")

    def _make_on_open(self, batch_data: List[Dict]):
        """Factory function to create on_open handler"""
        def on_open(ws):
            payload = self.create_ws_payload(batch_data)
            payload_json = json.dumps(payload)
            print(f"[TTS] Sending payload: {payload_json[:200]}...")  # Log first 200 chars
            ws.send(payload_json)

        return on_open


def time_to_microseconds(srt_time: str) -> int:
    """
    Convert SRT time format HH:MM:SS,mmm to microseconds

    Args:
        srt_time: Time in SRT format (e.g., "00:00:01,500")

    Returns:
        Time in microseconds
    """
    parts = srt_time.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid SRT time format: {srt_time}")

    hh = int(parts[0])
    mm = int(parts[1])
    ss_ms = parts[2].split(",")

    if len(ss_ms) != 2:
        raise ValueError(f"Invalid SRT time format: {srt_time}")

    ss = int(ss_ms[0])
    ms = int(ss_ms[1])

    total_micro = (hh * 3600 + mm * 60 + ss) * 1_000_000 + ms * 1000
    return total_micro


def get_wav_duration_ms(wav_path: str) -> float:
    """
    Get duration of WAV file in milliseconds using ffprobe

    Args:
        wav_path: Path to WAV file

    Returns:
        Duration in milliseconds
    """
    try:
        # Use ffprobe to get duration
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1:nokey=1",
            wav_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        duration_sec = float(result.stdout.strip())
        return duration_sec * 1000  # Convert to milliseconds

    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        return 0


def merge_wav_files(wav_files: List[str], output_path: str, subtitles: List[Dict]) -> str:
    """
    Merge WAV files synchronized with SRT subtitles

    Args:
        wav_files: List of WAV file paths (indexed by subtitle sequence)
        output_path: Output file path
        subtitles: List of subtitle dictionaries with start_time, end_time, content

    Returns:
        Base64 encoded audio data
    """
    if not wav_files or not subtitles:
        raise ValueError("WAV files and subtitles cannot be empty")

    try:
        tmp_dir = os.path.dirname(os.path.abspath(output_path)) or "."
        os.makedirs(tmp_dir, exist_ok=True)
        
        creation_flags = 0
        if os.name == 'nt':
            creation_flags = subprocess.CREATE_NO_WINDOW

        temp_files: List[str] = []
        concat_file = os.path.join(tmp_dir, f"{uuid.uuid4().hex}_concat.txt")
        
        # Process subtitles in order
        current_time_us = 0
        first_subtitle_start = time_to_microseconds(subtitles[0]["start_time"])
        
        # Add silence before first subtitle if needed
        if first_subtitle_start > 0:
            silence_duration = first_subtitle_start / 1_000_000
            silence_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}_silence.wav")
            _create_silence(silence_path, silence_duration, creation_flags)
            temp_files.append(silence_path)
            current_time_us = first_subtitle_start
        
        # Process each subtitle
        for idx, subtitle in enumerate(subtitles):
            start_time_us = time_to_microseconds(subtitle["start_time"])
            end_time_us = time_to_microseconds(subtitle["end_time"])
            subtitle_duration_us = end_time_us - start_time_us
            subtitle_duration_sec = subtitle_duration_us / 1_000_000
            
            # Add silence between subtitles if gap exists
            if current_time_us < start_time_us:
                gap_duration = (start_time_us - current_time_us) / 1_000_000
                silence_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}_silence.wav")
                _create_silence(silence_path, gap_duration, creation_flags)
                temp_files.append(silence_path)
            
            # Get corresponding WAV file (1-indexed)
            wav_path = wav_files[idx] if idx < len(wav_files) else None
            if not wav_path or not os.path.exists(wav_path):
                raise TTSError(f"WAV file not found for subtitle {idx + 1}")
            
            # Get audio duration
            audio_duration_ms = get_wav_duration_ms(wav_path)
            audio_duration_sec = audio_duration_ms / 1000
            
            # Trim silence from audio
            trimmed_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}_trimmed.wav")
            _trim_silence(wav_path, trimmed_path, creation_flags)
            trimmed_duration_ms = get_wav_duration_ms(trimmed_path)
            trimmed_duration_sec = trimmed_duration_ms / 1000
            
            # Adjust audio to match subtitle duration
            adjusted_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}_adjusted.wav")
            
            if abs(trimmed_duration_sec - subtitle_duration_sec) < 0.01:
                # Duration matches, use as-is
                adjusted_path = trimmed_path
            elif trimmed_duration_sec > subtitle_duration_sec:
                # Speed up audio
                speed_factor = trimmed_duration_sec / subtitle_duration_sec
                _speed_up_audio(trimmed_path, adjusted_path, speed_factor, creation_flags)
                if os.path.exists(trimmed_path) and trimmed_path != wav_path:
                    os.remove(trimmed_path)
            else:
                # Add silence to match duration
                silence_needed = subtitle_duration_sec - trimmed_duration_sec
                _pad_audio_with_silence(trimmed_path, adjusted_path, silence_needed, creation_flags)
                if os.path.exists(trimmed_path) and trimmed_path != wav_path:
                    os.remove(trimmed_path)
            
            temp_files.append(adjusted_path)
            current_time_us = end_time_us
        
        # Concatenate all files
        with open(concat_file, "w", encoding="utf-8") as f:
            for fpath in temp_files:
                f.write(f"file '{os.path.abspath(fpath)}'\n")
        
        cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output_path
        ]
        
        proc = subprocess.run(cmd, capture_output=True, creationflags=creation_flags, timeout=180)
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace")
            raise TTSError(f"ffmpeg concat failed: {stderr}")
        
        # Encode result to base64
        result = encode_wav_to_base64(output_path)
        
        # Cleanup temp files
        try:
            if os.path.exists(concat_file):
                os.remove(concat_file)
            for fpath in temp_files:
                if os.path.exists(fpath):
                    os.remove(fpath)
        except Exception:
            pass
        
        return result

    except subprocess.TimeoutExpired as e:
        raise TTSError(f"ffmpeg timeout while merging WAV files: {e}")
    except Exception as e:
        raise TTSError(f"Failed to merge WAV files: {str(e)}")


def _create_silence(output_path: str, duration_sec: float, creation_flags: int) -> None:
    """Create silence WAV file"""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=channel_layout=mono:sample_rate=24000",
        "-t", f"{duration_sec}", "-acodec", "pcm_s16le",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, creationflags=creation_flags, timeout=30)


def _trim_silence(input_path: str, output_path: str, creation_flags: int) -> None:
    """Trim silence from start and end of audio"""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-40dB:end_periods=1:end_duration=0.1:end_threshold=-40dB",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, creationflags=creation_flags, timeout=60)


def _speed_up_audio(input_path: str, output_path: str, speed_factor: float, creation_flags: int) -> None:
    """Speed up audio to match duration"""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-filter:a", f"atempo={speed_factor}",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, creationflags=creation_flags, timeout=60)


def _pad_audio_with_silence(input_path: str, output_path: str, pad_duration_sec: float, creation_flags: int) -> None:
    """Pad audio with silence at the end"""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", f"apad=pad_dur={pad_duration_sec}",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, creationflags=creation_flags, timeout=60)


def encode_wav_to_base64(wav_path: str) -> str:
    """
    Encode WAV file to base64 string

    Args:
        wav_path: Path to WAV file

    Returns:
        Base64 encoded string
    """
    try:
        with open(wav_path, "rb") as f:
            wav_data = f.read()
        return base64.b64encode(wav_data).decode("utf-8")
    except FileNotFoundError:
        raise TTSError(f"WAV file not found: {wav_path}")
    except Exception as e:
        raise TTSError(f"Failed to encode WAV file: {str(e)}")


def parse_srt_content(srt_content: str) -> List[Dict]:
    """
    Parse SRT content into structured subtitle data

    Args:
        srt_content: SRT file content as string

    Returns:
        List of subtitle dictionaries with keys: sequence, start_time, end_time, content
    """
    subtitles = []
    blocks = srt_content.strip().split("\n\n")

    for block in blocks:
        if not block.strip():
            continue

        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        try:
            sequence = int(lines[0].strip())
            time_parts = lines[1].strip().split(" --> ")

            if len(time_parts) != 2:
                continue

            start_time = time_parts[0].strip()
            end_time = time_parts[1].strip()
            content = " ".join(lines[2:]).strip()

            subtitles.append({
                "sequence": sequence,
                "start_time": start_time,
                "end_time": end_time,
                "content": content
            })
        except (ValueError, IndexError):
            continue

    return subtitles

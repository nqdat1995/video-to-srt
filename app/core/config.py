"""Application configuration"""

import os
from typing import Optional


class Settings:
   """Application settings"""

   # App metadata
   APP_NAME: str = "Video Subtitle OCR → SRT (PaddleOCR v3)"
   VERSION: str = "1.1.0"
   DESCRIPTION: str = "Extract subtitles from video using OCR"

   # OCR Cache settings
   OCR_CACHE_MAX: int = int(os.getenv("OCR_CACHE_MAX", "4"))
   BATCH_OCR_SIZE: int = int(os.getenv("BATCH_OCR_SIZE", "8"))

   # Logging level
   LOG_LEVEL: str = os.getenv("LOG_LEVEL", "ERROR").upper()

   # Video processing defaults with environment variables
   # DEFAULT_TARGET_FPS: Frames per second for sampling (1-32, default: 4.0)
   # Set via environment: export DEFAULT_TARGET_FPS=6.0
   _target_fps = float(os.getenv("DEFAULT_TARGET_FPS", "4.0"))
   DEFAULT_TARGET_FPS: float = max(1.0, min(32.0, _target_fps))
   
   # Log warning if value was out of range
   if _target_fps != DEFAULT_TARGET_FPS:
       import warnings
       warnings.warn(
           f"DEFAULT_TARGET_FPS out of range [1.0, 32.0]. "
           f"Given: {_target_fps}, Using: {DEFAULT_TARGET_FPS}"
       )
   
   DEFAULT_BOTTOM_START: float = 0.0  # 0.0 = auto-detect subtitle region (if possible), else use full frame
   DEFAULT_MAX_WIDTH: int = 1280
   DEFAULT_ENHANCE: bool = True

   # OCR defaults (PaddleOCR 3.x auto-selects PP-OCRv5 based on lang)
   DEFAULT_LANG: str = "vi"  # Language code, auto-selects best model
   DEFAULT_DEVICE: str = "cpu"  # "cpu" or "gpu:0", "gpu:1", etc.
   DEFAULT_DET_MODEL: str = "PP-OCRv5_mobile_det"  # Legacy, not used in 3.x
   DEFAULT_REC_MODEL: str = "PP-OCRv5_mobile_rec"  # Legacy, not used in 3.x
   DEFAULT_CONF_MIN: float = 0.5  # Minimum confidence threshold

   # Hash gating
   DEFAULT_HASH_DIST_THR: int = 6

   # Debouncing
   DEFAULT_DEBOUNCE_FRAMES: int = 2
   DEFAULT_EMPTY_DEBOUNCE_FRAMES: int = 2
   DEFAULT_SIM_THR: float = 0.90

   # SRT cleanup
   DEFAULT_MIN_DURATION_MS: int = 400
   DEFAULT_MERGE_GAP_MS: int = 250

   # Letterbox detection
   LUMA_THRESHOLD: int = 18
   ROW_BLACK_RATIO_THR: float = 0.98
   MAX_BAR_FRACTION: float = 0.25

   # CLAHE enhancement
   CLAHE_CLIP_LIMIT: float = 2.0
   CLAHE_TILE_GRID_SIZE: tuple = (8, 8)

   # Text assembly
   LINE_Y_GAP_PX: int = 18

   # TTS (Text-to-Speech) Settings
   TTS_ENABLED: bool = os.getenv("TTS_ENABLED", "true").lower() == "true"
   TTS_API_KEY: str = os.getenv("TTS_API_KEY", "ddjeqjLGMn")
   TTS_API_TOKEN: str = os.getenv("TTS_API_TOKEN", "MTIzNDU2Nzg5YWJjZGVmZx+91sTg0sWUUldexSN5RTG6Ib0KFIDfjJKUzFKs4K/yf7DGAm1lSETIdxTtbo/tKcl1PLZjSekz3hNDeEa0+pQ0Gk41FkIxDTQHtJ1zysLKYlZY8tS1/gXUB2Xg85H+ZFOzwHC54BQIX8kmeW9awYMqNx3dQYkLazc58hL20z0BbPB+46k0iGmkQRc1eCWuePT0evdNMnIuOKFjqF6WcX1oDEq6U1SJGCPqbsnbLsKRF5TQSUZKPzh504jGfRfpn76HXQXQG4/LFb8ipmK31So9XKBpKyRoeYL7jNIRG7keK+S5WlDco6ShFyuX16bYwUfMI7vSGULq6vWLAlDEGju8RZEsPrlnfbT4/YoZqAKRDLnnuZG2KQMl4XSvTgBogj/h33/Ke2orXSJVGBAqGuu7J7d8fwxm9CbMaZ8TbAzmTfaLlEE5+78+Wk+Av7lds/C6Y3amkLgzMWH3O4hmOpU12GOEQb9xwi5eB1Zn2YqkAvvGmLD+M6an69sut8iBk8onSxbv5whtLwKrdwLCWNzrIs8pK39pYgt/Dkg/Ansyin2POO/ih83j4zaiJMufAlMQb/pPxnClHyipVvWNQRiO501IB+TKXEQJ303ZiVJKWZhWbjyhzg2rUSZFr3ldVZ4L0o6sIqvmqmiFbwqcMmE5ZBkswLTM79IcoiyNMHL7/h9YFAs9LquaGH7Gn8d3lg==")
   TTS_DEFAULT_VOICE: str = os.getenv("TTS_DEFAULT_VOICE", "BV074_streaming")
   TTS_OUTPUT_DIR: str = os.getenv("TTS_OUTPUT_DIR", "./tts_output")
   TTS_TEMP_DIR: str = os.getenv("TTS_TEMP_DIR", "./tts_temp")
   TTS_BATCH_SIZE: int = int(os.getenv("TTS_BATCH_SIZE", "1000"))
   TTS_MAX_RETRIES: int = int(os.getenv("TTS_MAX_RETRIES", "3"))
   
   # Audio output settings
   AUDIO_OUTPUT_DIR: str = os.getenv("AUDIO_OUTPUT_DIR", "./audio_output")
   MAX_AUDIOS_PER_USER: int = int(os.getenv("MAX_AUDIOS_PER_USER", "50"))

   # Database settings
   DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://video_user:video_password@localhost:5432/video_srt_db")
   
   # Upload settings
   UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
   MAX_VIDEOS_PER_USER: int = int(os.getenv("MAX_VIDEOS_PER_USER", "10"))
   MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))
   ALLOWED_VIDEO_FORMATS: list = ["mp4", "avi", "mov", "mkv", "flv", "wmv", "webm"]
   
   # SRT output settings
   SRT_OUTPUT_DIR: str = os.getenv("SRT_OUTPUT_DIR", "./srt_output")
   
   # SRT temporary files settings
   SRT_TEMP_DIR: str = os.getenv("SRT_TEMP_DIR", "./srt_temp")

settings = Settings()

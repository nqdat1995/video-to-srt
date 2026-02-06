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
   
   DEFAULT_BOTTOM_START: float = 0.55
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


settings = Settings()

"""OCR service for text recognition"""

import time
import logging
import threading
import sys
import os
import io
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from paddleocr import PaddleOCR

from ..models.internal import OcrEntry
from ..core.config import settings

# Suppress PaddleOCR verbose logging
logging.getLogger("ppocr").setLevel(logging.ERROR)
logging.getLogger('paddleocr').setLevel(logging.ERROR)
logging.getLogger('paddle').setLevel(logging.ERROR)
logging.getLogger('paddlex').setLevel(logging.ERROR)

@contextmanager
def suppress_paddleocr_output():
    """Context manager to suppress all PaddleOCR output (stdout, stderr, and logging)"""
    # Save original stdout/stderr
    stdout_backup = sys.stdout
    stderr_backup = sys.stderr
    
    # Create a NullWriter that discards everything
    null = io.StringIO()
    
    # Disable paddleocr logging temporarily
    paddleocr_logger = logging.getLogger('paddleocr')
    paddle_logger = logging.getLogger('paddle')
    old_paddleocr_disabled = paddleocr_logger.disabled
    old_paddle_disabled = paddle_logger.disabled
    
    try:
        # Redirect stdout/stderr and disable loggers
        sys.stdout = null
        sys.stderr = null
        paddleocr_logger.disabled = True
        paddle_logger.disabled = True
        yield
    finally:
        # Restore everything
        sys.stdout = stdout_backup
        sys.stderr = stderr_backup
        paddleocr_logger.disabled = old_paddleocr_disabled
        paddle_logger.disabled = old_paddle_disabled


# Supported languages in PaddleOCR 3.x
SUPPORTED_LANGUAGES = {
    'ch', 'en', 'fr', 'de', 'es', 'pt', 'ru', 'ja', 'ko', 'vi', 'ar', 
    'hi', 'my', 'th', 'kh', 'la', 'fa', 'ug', 'ur', 'ps', 'sd', 'bn',
    'as', 'gu', 'kn', 'ml', 'mr', 'or', 'pa', 'ta', 'te', 'uk', 'be',
    'bg', 'hr', 'sr', 'sk', 'sl', 'sq', 'sv', 'pl', 'lt', 'lv', 'et',
    'hu', 'cs', 'ro', 'tr'
}


class OcrService:
   """Service for managing OCR engines and text recognition"""

   def __init__(self):
       self._cache: Dict[str, OcrEntry] = {}
       self._cache_lock = threading.Lock()
       self._cache_max = settings.OCR_CACHE_MAX
       self._batch_size = settings.BATCH_OCR_SIZE

   def _cache_key(
       self,
       lang: str,
       device: str,
       det_model: str,
       rec_model: str,
       use_textline_orientation: bool
   ) -> str:
       """Generate cache key for OCR engine (PaddleOCR 3.x)"""
       # Note: In 3.x, built-in models are selected by lang parameter
       # det_model/rec_model are kept for compatibility but not used in constructor
       return f"lang={lang}|device={device}|angle_cls={int(use_textline_orientation)}"

   def get_engine(
       self,
       lang: str,
       device: str,
       det_model: str,
       rec_model: str,
       use_textline_orientation: bool
   ) -> OcrEntry:
       """
       Get or create OCR engine with caching

       Args:
           lang: Language code
           device: Device to use (cpu/gpu)
           det_model: Detection model name
           rec_model: Recognition model name
           use_textline_orientation: Whether to detect text orientation

       Returns:
           Cached OCR entry
       """
       # Normalize language code
       lang = lang.lower().strip()
       
       # Validate language
       if lang not in SUPPORTED_LANGUAGES:
           raise ValueError(
               f"Language '{lang}' is not supported. "
               f"Supported languages: {', '.join(sorted(SUPPORTED_LANGUAGES))}"
           )
       
       now = time.time()
       key = self._cache_key(lang, device, det_model, rec_model, use_textline_orientation)

       with self._cache_lock:
           if key in self._cache:
               self._cache[key].last_used = now
               return self._cache[key]

           # Evict LRU entry if cache is full
           if len(self._cache) >= self._cache_max:
               lru_key = min(self._cache.items(), key=lambda kv: kv[1].last_used)[0]
               self._cache.pop(lru_key, None)

           # Create new engine with OneDNN disabled to avoid compatibility issues
           # OneDNN can cause NotImplementedError with certain model configurations
           try:
               import os
               import logging
               
               # Disable OneDNN backend to avoid inference errors
               os.environ['PADDLE_DISBLE_FAST_FC'] = '1'
               os.environ['FLAGS_use_mkldnn'] = '0'
               
               # Temporarily suppress logging and output during PaddleOCR initialization
               # PaddleOCR has its own logging that we need to suppress
               logging.disable(logging.CRITICAL)
               
               try:
                   with suppress_paddleocr_output():
                       engine = PaddleOCR(
                           lang=lang,
                           use_angle_cls=use_textline_orientation,
                           use_gpu=True,  # Ensure CPU mode to avoid GPU-specific issues
                           show_log=False  # Disable PaddleOCR's internal logging
                       )
               finally:
                   logging.disable(logging.NOTSET)  # Re-enable logging
               
           except ValueError as e:
               # Handle model download/initialization errors
               raise ValueError(
                   f"Failed to initialize PaddleOCR for language '{lang}': {str(e)}. "
                   f"This may be due to network issues or model unavailability. "
                   f"Try again or use a different language."
               )
           
           entry = OcrEntry(engine=engine, lock=threading.Lock(), last_used=now)
           self._cache[key] = entry
           return entry

   def run_ocr(
       self,
       entry: OcrEntry,
       img_bgr: np.ndarray
   ) -> Tuple[List[str], List[float], Optional[np.ndarray]]:
       """
       Run OCR on single image (PaddleOCR 3.x)

       Args:
           entry: OCR engine entry
           img_bgr: BGR image

       Returns:
           Tuple of (texts, scores, polygons)
       """
       img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

       with entry.lock:
           # Suppress all PaddleOCR output during inference
           with suppress_paddleocr_output():
               # PaddleOCR 3.x returns: [[bbox, (text, score)], ...] or None
               result = entry.engine.ocr(img_rgb)

       # Handle empty or None results
       if not result or not result[0]:
           return [], [], None

       # Parse PaddleOCR 3.x output format
       # result[0] contains list of [bbox, (text, score)] for each detected text
       texts = []
       scores = []
       polys = []

       for line in result[0]:
           if line and len(line) >= 2:
               bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
               text_info = line[1]  # (text, score)

               if isinstance(text_info, (tuple, list)) and len(text_info) >= 2:
                   text = text_info[0]
                   score = text_info[1]

                   texts.append(str(text))
                   scores.append(float(score))
                   polys.append(np.array(bbox))

       return texts, scores, np.array(polys) if polys else None

   def run_ocr_batch(
       self,
       entry: OcrEntry,
       img_bgr_list: List[np.ndarray]
   ) -> List[Tuple[List[str], List[float], Optional[np.ndarray]]]:
       """
       Run OCR on batch of images for GPU optimization (PaddleOCR 3.x)

       Args:
           entry: OCR engine entry
           img_bgr_list: List of BGR images

       Returns:
           List of (texts, scores, polygons) tuples
       """
       if not img_bgr_list:
           return []

       img_rgb_list = [cv2.cvtColor(img, cv2.COLOR_BGR2RGB) for img in img_bgr_list]

       results = []
       with entry.lock:
           # Suppress all PaddleOCR output during batch inference
           with suppress_paddleocr_output():
               for img_rgb in img_rgb_list:
                   # PaddleOCR 3.x API
                   result = entry.engine.ocr(img_rgb)

                   if not result or not result[0]:
                       results.append(([], [], None))
                       continue

                   # Parse PaddleOCR 3.x output
                   texts = []
                   scores = []
                   polys = []

                   for line in result[0]:
                       if line and len(line) >= 2:
                           bbox = line[0]
                           text_info = line[1]

                           if isinstance(text_info, (tuple, list)) and len(text_info) >= 2:
                               text = text_info[0]
                               score = text_info[1]

                               texts.append(str(text))
                               scores.append(float(score))
                               polys.append(np.array(bbox))

                   poly_array = np.array(polys) if polys else None
                   results.append((texts, scores, poly_array))

       return results

   def assemble_subtitle_text(
       self,
       texts: List[str],
       scores: List[float],
       polys: Optional[np.ndarray],
       conf_min: float,
       line_y_gap_px: int = None
   ) -> str:
       """
       Assemble multiple text detections into single subtitle

       Args:
           texts: Detected text strings
           scores: Confidence scores
           polys: Detection polygons
           conf_min: Minimum confidence threshold
           line_y_gap_px: Y-gap for line grouping

       Returns:
           Assembled subtitle text
       """
       from ..utils.text_utils import normalize_text

       if line_y_gap_px is None:
           line_y_gap_px = settings.LINE_Y_GAP_PX

       items = []
       for i, t in enumerate(texts):
           t = (t or "").strip()
           if not t:
               continue
           sc = scores[i] if i < len(scores) else 0.0
           if sc < conf_min:
               continue

           # Estimate y, x from polygon if available
           y = 0.0
           x = 0.0
           if polys is not None and i < len(polys):
               poly = np.array(polys[i])
               xs = poly[:, 0]
               ys = poly[:, 1]
               y = float(np.mean(ys))
               x = float(np.mean(xs))

           items.append((y, x, t))

       if not items:
           return ""

       items.sort(key=lambda z: (z[0], z[1]))

       # Group into lines by y coordinate
       lines: List[List[str]] = []
       cur_y = None
       for y, x, t in items:
           if cur_y is None or abs(y - cur_y) <= line_y_gap_px:
               if cur_y is None:
                   cur_y = y
               lines.append(lines.pop() + [t] if lines else [t])
           else:
               lines.append([t])
               cur_y = y

       out_lines = [" ".join(ln).strip() for ln in lines if ln]
       return normalize_text("\n".join(out_lines))


# Singleton instance
ocr_service = OcrService()

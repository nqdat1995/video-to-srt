"""Internal data models"""
import threading
from dataclasses import dataclass
from collections import Counter
from paddleocr import PaddleOCR


@dataclass
class OcrEntry:
   """OCR engine cache entry"""

   engine: PaddleOCR
   lock: threading.Lock
   last_used: float


@dataclass
class CueDraft:
   """Draft subtitle cue being assembled"""

   start: float
   last: float
   text_votes: Counter

"""Internal data models"""
import threading
from dataclasses import dataclass, field
from collections import Counter
from typing import List, Tuple
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
   bbox_list: List[Tuple[float, float, float, float]] = field(default_factory=list)  # List of (x1, y1, x2, y2)

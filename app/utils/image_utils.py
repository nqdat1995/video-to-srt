"""Image processing utilities"""

from typing import Tuple
import cv2
import numpy as np

from ..core.config import settings


def detect_active_vertical_region(
   frame_bgr: np.ndarray,
   luma_thr: int = None,
   row_black_ratio_thr: float = None,
   max_bar_fraction: float = None
) -> Tuple[int, int]:
   """
   Detect active region of frame by removing letterbox bars

   Args:
       frame_bgr: BGR frame
       luma_thr: Luminance threshold for black detection
       row_black_ratio_thr: Ratio threshold for black rows
       max_bar_fraction: Maximum allowed bar size as fraction of height

   Returns:
       Tuple of (top, bottom) pixel coordinates
   """
   if luma_thr is None:
       luma_thr = settings.LUMA_THRESHOLD
   if row_black_ratio_thr is None:
       row_black_ratio_thr = settings.ROW_BLACK_RATIO_THR
   if max_bar_fraction is None:
       max_bar_fraction = settings.MAX_BAR_FRACTION

   h, w = frame_bgr.shape[:2]
   gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
   ds_w = min(320, w)
   gray_small = cv2.resize(gray, (ds_w, h), interpolation=cv2.INTER_AREA)

   black = (gray_small <= luma_thr).astype(np.uint8)
   row_ratio = black.mean(axis=1)

   top = 0
   for y in range(h):
       if row_ratio[y] >= row_black_ratio_thr:
           top = y + 1
       else:
           break

   bottom = h
   for y in range(h - 1, -1, -1):
       if row_ratio[y] >= row_black_ratio_thr:
           bottom = y
       else:
           break

   max_bar = int(h * max_bar_fraction)
   if top > max_bar:
       top = 0
   if (h - bottom) > max_bar:
       bottom = h

   if bottom - top < int(h * 0.5):
       return 0, h

   return top, bottom


def enhance_roi(roi_bgr: np.ndarray) -> np.ndarray:
   """
   Enhance ROI using CLAHE on L channel

   Args:
       roi_bgr: BGR image region

   Returns:
       Enhanced BGR image
   """
   lab = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2LAB)
   l, a, b = cv2.split(lab)
   clahe = cv2.createCLAHE(
       clipLimit=settings.CLAHE_CLIP_LIMIT,
       tileGridSize=settings.CLAHE_TILE_GRID_SIZE
   )
   l2 = clahe.apply(l)
   out = cv2.cvtColor(cv2.merge([l2, a, b]), cv2.COLOR_LAB2BGR)
   return out

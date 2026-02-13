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


def detect_subtitle_region(
    frame_bgr: np.ndarray,
    text_density_thr: float = 0.01
) -> float:
   """
   Auto-detect subtitle region by finding where text density is highest
   
   Subtitles typically appear in the lower part of video, but this function
   detects the actual region where text starts.

   Args:
       frame_bgr: BGR frame
       text_density_thr: Minimum pixel density threshold to detect text region

   Returns:
       bottom_start value (0.0-1.0) - fraction of frame height where subtitle region starts
   """
   h, w = frame_bgr.shape[:2]
   gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
   
   # Detect edges (likely to contain text)
   edges = cv2.Canny(gray, 50, 150)
   
   # Calculate row-wise edge density (normalize by width)
   row_density = edges.sum(axis=1) / (w * 255.0)
   
   # Find where text density becomes significant (moving from bottom upward)
   significant_thr = text_density_thr
   text_start_y = h - 1
   
   for y in range(h - 1, -1, -1):
       if row_density[y] >= significant_thr:
           text_start_y = y
       else:
           # If we find a gap (no text), stop searching upward
           if text_start_y < h - 1:
               break
   
   # Convert to fraction (0.0 = top, 1.0 = bottom)
   bottom_start = max(0.0, (text_start_y - 100) / h)  # 100px margin above text
   
   return min(bottom_start, 1.0)


def detect_roi_content_change(
    prev_roi: np.ndarray,
    curr_roi: np.ndarray,
    change_thr: float = 0.15
) -> bool:
   """
   Detect significant content change in ROI region (subtle text changes)
   
   This complements hash-based gating by detecting actual content changes
   like new text appearing or text changing, which hash might miss due to
   compression artifacts or subtle differences.

   Args:
       prev_roi: Previous ROI frame
       curr_roi: Current ROI frame
       change_thr: Threshold for detecting change (0.0-1.0)

   Returns:
       True if significant change detected, False otherwise
   """
   if prev_roi is None or curr_roi is None:
       return True
   
   if prev_roi.shape != curr_roi.shape:
       return True
   
   # Convert to grayscale
   prev_gray = cv2.cvtColor(prev_roi, cv2.COLOR_BGR2GRAY)
   curr_gray = cv2.cvtColor(curr_roi, cv2.COLOR_BGR2GRAY)
   
   # Detect edges (text contains edges)
   prev_edges = cv2.Canny(prev_gray, 30, 100)
   curr_edges = cv2.Canny(curr_gray, 30, 100)
   
   # Calculate difference in edge patterns
   diff = cv2.absdiff(prev_edges, curr_edges)
   
   # Calculate percentage of pixels that changed
   change_ratio = diff.sum() / (diff.shape[0] * diff.shape[1] * 255.0)
   
   return change_ratio > change_thr


def detect_text_motion(
    prev_roi: np.ndarray,
    curr_roi: np.ndarray,
    motion_thr: float = 0.10
) -> bool:
   """
   Detect text motion/movement (new text appearing or text fading)
   
   Useful for catching transitions between subtitles that might have
   similar static content but different positioning or appearance.

   Args:
       prev_roi: Previous ROI frame
       curr_roi: Current ROI frame
       motion_thr: Threshold for detecting motion (0.0-1.0)

   Returns:
       True if motion detected, False otherwise
   """
   if prev_roi is None or curr_roi is None:
       return True
   
   if prev_roi.shape != curr_roi.shape:
       return True
   
   # Convert to grayscale
   prev_gray = cv2.cvtColor(prev_roi, cv2.COLOR_BGR2GRAY)
   curr_gray = cv2.cvtColor(curr_roi, cv2.COLOR_BGR2GRAY)
   
   # Compute optical flow (motion)
   flow = cv2.calcOpticalFlowFarneback(
       prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
   )
   
   # Calculate magnitude of motion
   mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
   
   # Calculate percentage of pixels with significant motion
   motion_ratio = (mag > 1.0).sum() / (mag.shape[0] * mag.shape[1])
   
   return motion_ratio > motion_thr


def detect_text_presence_change(
    prev_roi: np.ndarray,
    curr_roi: np.ndarray,
    presence_thr: float = 0.30
) -> bool:
   """
   Detect significant change in text presence (text appearing/disappearing)
   
   Handles edge cases like:
   - Empty frame → text frame (text appears)
   - Text frame → empty frame (text disappears)
   - Long subtitle → short subtitle (major content reduction)
   
   Uses multiple indicators for robust detection.

   Args:
       prev_roi: Previous ROI frame
       curr_roi: Current ROI frame
       presence_thr: Threshold for detecting presence change (0.0-1.0)

   Returns:
       True if significant presence change detected, False otherwise
   """
   if prev_roi is None or curr_roi is None:
       return True
   
   if prev_roi.shape != curr_roi.shape:
       return True
   
   # Convert to grayscale
   prev_gray = cv2.cvtColor(prev_roi, cv2.COLOR_BGR2GRAY)
   curr_gray = cv2.cvtColor(curr_roi, cv2.COLOR_BGR2GRAY)
   
   # Method 1: Edge density change (text has edges)
   prev_edges = cv2.Canny(prev_gray, 30, 100)
   curr_edges = cv2.Canny(curr_gray, 30, 100)
   
   prev_edge_ratio = prev_edges.sum() / (prev_edges.shape[0] * prev_edges.shape[1] * 255.0)
   curr_edge_ratio = curr_edges.sum() / (curr_edges.shape[0] * curr_edges.shape[1] * 255.0)
   
   # Large change in edge density = presence change
   edge_change_ratio = abs(curr_edge_ratio - prev_edge_ratio) / (prev_edge_ratio + 1e-6)
   
   if edge_change_ratio > presence_thr:
       return True
   
   # Method 2: Intensity variance change (uniform frame vs text frame)
   prev_variance = float(cv2.Laplacian(prev_gray, cv2.CV_64F).var())
   curr_variance = float(cv2.Laplacian(curr_gray, cv2.CV_64F).var())
   
   # Text frames have higher variance than blank frames
   variance_change_ratio = abs(curr_variance - prev_variance) / (prev_variance + 1e-6)
   
   if variance_change_ratio > presence_thr:
       return True
   
   # Method 3: Histogram change (color distribution)
   prev_hist = cv2.calcHist([prev_gray], [0], None, [256], [0, 256])
   curr_hist = cv2.calcHist([curr_gray], [0], None, [256], [0, 256])
   
   # Normalize histograms
   prev_hist = cv2.normalize(prev_hist, prev_hist).flatten()
   curr_hist = cv2.normalize(curr_hist, curr_hist).flatten()
   
   # Compare histograms using Chi-Square distance
   hist_distance = cv2.compareHist(prev_hist, curr_hist, cv2.HISTCMP_CHISQR)
   
   # Normalize distance (0-1 range approximately)
   hist_change_ratio = min(1.0, hist_distance / 10.0)
   
   if hist_change_ratio > presence_thr:
       return True
   
   return False


def detect_intensity_spike(
    prev_roi: np.ndarray,
    curr_roi: np.ndarray,
    spike_thr: float = 0.25
) -> bool:
   """
   Detect sudden intensity changes (sudden brightness increase/decrease)
   
   Useful for catching:
   - Empty/dark frame → bright text frame
   - Bright frame → dark/empty frame
   - Major lighting changes affecting subtitle visibility
   
   Args:
       prev_roi: Previous ROI frame
       curr_roi: Current ROI frame
       spike_thr: Threshold for detecting spike (0.0-1.0)

   Returns:
       True if intensity spike detected, False otherwise
   """
   if prev_roi is None or curr_roi is None:
       return True
   
   if prev_roi.shape != curr_roi.shape:
       return True
   
   # Convert to grayscale
   prev_gray = cv2.cvtColor(prev_roi, cv2.COLOR_BGR2GRAY)
   curr_gray = cv2.cvtColor(curr_roi, cv2.COLOR_BGR2GRAY)
   
   # Calculate mean intensity
   prev_mean = float(prev_gray.mean())
   curr_mean = float(curr_gray.mean())
   
   # Calculate relative change in intensity
   intensity_change = abs(curr_mean - prev_mean) / (prev_mean + 1e-6)
   
   # Also check if mean changed significantly in absolute terms
   intensity_diff = abs(curr_mean - prev_mean)
   
   # Trigger on either relative change OR absolute change
   return intensity_change > spike_thr or intensity_diff > 30

"""SRT generation service"""

from typing import List, Tuple, Dict, Any
from collections import Counter

from ..models.internal import CueDraft
from ..utils.text_utils import srt_timestamp, similarity


class SrtService:
   """Service for SRT subtitle generation"""

   @staticmethod
   def finalize_cue(cue: CueDraft) -> Tuple[float, float, str, List[Tuple[float, float, float, float]]]:
       """
       Finalize cue by selecting most common text

       Args:
           cue: Draft cue

       Returns:
           Tuple of (start_time, end_time, text, bbox_list)
       """
       text = cue.text_votes.most_common(1)[0][0] if cue.text_votes else ""
       return cue.start, cue.last, text, cue.bbox_list

   @staticmethod
   def merge_and_filter_cues(
       cues: List[Tuple[float, float, str, List[Tuple[float, float, float, float]]]],
       min_duration_ms: int,
       merge_gap_ms: int,
       sim_thr: float
   ) -> List[Tuple[float, float, str, List[Tuple[float, float, float, float]]]]:
       """
       Merge and filter cues based on duration and similarity

       Args:
           cues: List of raw cues with bbox info
           min_duration_ms: Minimum cue duration in milliseconds
           merge_gap_ms: Maximum gap for merging in milliseconds
           sim_thr: Similarity threshold for merging

       Returns:
           Filtered and merged cues
       """
       if not cues:
           return []

       # Filter by minimum duration
       min_d = min_duration_ms / 1000.0
       cues = [(s, e, t, b) for (s, e, t, b) in cues if (e - s) >= min_d and t.strip()]

       # Merge adjacent cues with same text and small gap
       gap = merge_gap_ms / 1000.0
       merged = []
       for s, e, t, b in cues:
           if not merged:
               merged.append([s, e, t, b])
               continue
           ps, pe, pt, pb = merged[-1]
           # Fix: Kiểm tra khoảng cách chính xác - không merge nếu cue hiện tại bắt đầu trước khi cue trước kết thúc
           # và không kéo dài thời gian của cue trước nếu nó sẽ chồng lấp với cue tiếp theo
           if (s - pe) <= gap and (s - pe) >= 0 and similarity(t, pt) >= sim_thr:
               # Chỉ merge nếu thời gian không chồng lấp (s >= pe)
               merged[-1][1] = e
               # Merge bbox info (take average or union)
               if b:
                   merged[-1][3].extend(b)
           else:
               merged.append([s, e, t, b])

       return [(a, b, c, d) for a, b, c, d in merged]

   @staticmethod
   def cues_to_srt(cues: List[Tuple[float, float, str, List[Tuple[float, float, float, float]]]]) -> str:
       """
       Convert cues to SRT format

       Args:
           cues: List of (start, end, text, bbox_list) tuples

       Returns:
           SRT formatted string
       """
       lines = []
       for i, (s, e, t, b) in enumerate(cues, start=1):
           lines.append(str(i))
           lines.append(f"{srt_timestamp(s)} --> {srt_timestamp(e)}")
           lines.append(t)
           lines.append("")
       return "\n".join(lines).strip() + "\n"

   @staticmethod
   def generate_srt_details(
       cues: List[Tuple[float, float, str, List[Tuple[float, float, float, float]]]]
   ) -> List[Dict[str, Any]]:
       """
       Generate detailed SRT information with coordinates

       Args:
           cues: List of (start, end, text, bbox_list) tuples

       Returns:
           List of SRT detail dictionaries
       """
       srt_details = []
       for s, e, t, bbox_list in cues:
           srt_time = f"{srt_timestamp(s)} --> {srt_timestamp(e)}"
           
           # Get bounding box info - use first bbox or default values
           if bbox_list:
               # Calculate average coordinates from all bboxes
               x_coords = [b[0] for b in bbox_list] + [b[2] for b in bbox_list]
               y_coords = [b[1] for b in bbox_list] + [b[3] for b in bbox_list]
               x1 = min(x_coords) if x_coords else 0.0
               y1 = min(y_coords) if y_coords else 0.0
               x2 = max(x_coords) if x_coords else 0.0
               y2 = max(y_coords) if y_coords else 0.0
           else:
               x1, y1, x2, y2 = 0.0, 0.0, 0.0, 0.0
           
           srt_details.append({
               "srt": t,
               "srt_time": srt_time,
               "x1": x1,
               "y1": y1,
               "x2": x2,
               "y2": y2
           })
       
       return srt_details


# Singleton instance
srt_service = SrtService()

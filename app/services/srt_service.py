"""SRT generation service"""

from typing import List, Tuple
from collections import Counter

from ..models.internal import CueDraft
from ..utils.text_utils import srt_timestamp, similarity


class SrtService:
   """Service for SRT subtitle generation"""

   @staticmethod
   def finalize_cue(cue: CueDraft) -> Tuple[float, float, str]:
       """
       Finalize cue by selecting most common text

       Args:
           cue: Draft cue

       Returns:
           Tuple of (start_time, end_time, text)
       """
       text = cue.text_votes.most_common(1)[0][0] if cue.text_votes else ""
       return cue.start, cue.last, text

   @staticmethod
   def merge_and_filter_cues(
       cues: List[Tuple[float, float, str]],
       min_duration_ms: int,
       merge_gap_ms: int,
       sim_thr: float
   ) -> List[Tuple[float, float, str]]:
       """
       Merge and filter cues based on duration and similarity

       Args:
           cues: List of raw cues
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
       cues = [(s, e, t) for (s, e, t) in cues if (e - s) >= min_d and t.strip()]

       # Merge adjacent cues with same text and small gap
       gap = merge_gap_ms / 1000.0
       merged = []
       for s, e, t in cues:
           if not merged:
               merged.append([s, e, t])
               continue
           ps, pe, pt = merged[-1]
           if (s - pe) <= gap and similarity(t, pt) >= sim_thr:
               merged[-1][1] = max(pe, e)
           else:
               merged.append([s, e, t])

       return [(a, b, c) for a, b, c in merged]

   @staticmethod
   def cues_to_srt(cues: List[Tuple[float, float, str]]) -> str:
       """
       Convert cues to SRT format

       Args:
           cues: List of (start, end, text) tuples

       Returns:
           SRT formatted string
       """
       lines = []
       for i, (s, e, t) in enumerate(cues, start=1):
           lines.append(str(i))
           lines.append(f"{srt_timestamp(s)} --> {srt_timestamp(e)}")
           lines.append(t)
           lines.append("")
       return "\n".join(lines).strip() + "\n"


# Singleton instance
srt_service = SrtService()

"""SRT generation service"""

from typing import List, Tuple, Dict, Any

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

   @staticmethod
   def srt_to_ass(srt_content: str, fontname: str = "Arial", fontsize: int = 20, subtitle_y_position: int = 90) -> str:
       """
       Convert SRT subtitle content to ASS (Advanced SubStation Alpha) format with styling

       Args:
           srt_content: SRT subtitle content
           fontname: Font name for subtitles
           fontsize: Font size for subtitles
           subtitle_y_position: Vertical position as percentage (0=top, 100=bottom)

       Returns:
           ASS format subtitle content
       """
       lines = srt_content.strip().split('\n')
       
       # Calculate alignment and MarginV based on subtitle_y_position
       # Alignment values: 1-9 like numpad
       # 1=bottom-left, 2=bottom-center, 3=bottom-right
       # 4=middle-left, 5=middle-center, 6=middle-right
       # 7=top-left, 8=top-center, 9=top-right
       
       if subtitle_y_position <= 33:  # Top
           alignment = 8  # top-center
           margin_v = int(subtitle_y_position * 2.5)  # Scale for top position
       elif subtitle_y_position <= 66:  # Middle
           alignment = 5  # middle-center
           margin_v = int((50 - abs(50 - subtitle_y_position)) * 2.5)  # Scale for middle
       else:  # Bottom
           alignment = 2  # bottom-center
           margin_v = int((100 - subtitle_y_position) * 2.5)  # Scale for bottom position
       
       # ASS header with calculated alignment and margin
       ass_content = f"""[Script Info]
Title: Default Aegisub file
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{fontname},{fontsize},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,{alignment},0,0,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
       
       i = 0
       while i < len(lines):
           line = lines[i].strip()
           
           # Skip empty lines
           if not line:
               i += 1
               continue
           
           # Check if this is a cue number (numeric line)
           if line.isdigit():
               i += 1
               if i < len(lines):
                   time_line = lines[i].strip()
                   if '-->' in time_line:
                       # Parse timing
                       parts = time_line.split('-->')
                       if len(parts) == 2:
                           start = parts[0].strip()
                           end = parts[1].strip()
                           
                           # Convert SRT time format (HH:MM:SS,mmm) to ASS format (H:MM:SS.cc)
                           start_ass = SrtService._convert_time_to_ass(start)
                           end_ass = SrtService._convert_time_to_ass(end)
                           
                           i += 1
                           # Collect text lines
                           text_lines = []
                           while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                               text_lines.append(lines[i].strip())
                               i += 1
                           
                           text = '\\N'.join(text_lines)  # ASS uses \N for newlines
                           ass_content += f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{text}\n"
                   else:
                       i += 1
           else:
               i += 1
       
       return ass_content

   @staticmethod
   def _convert_time_to_ass(time_str: str) -> str:
       """
       Convert SRT time format (HH:MM:SS,mmm) to ASS format (H:MM:SS.cc)
       
       Args:
           time_str: Time in SRT format
           
       Returns:
           Time in ASS format
       """
       # Remove trailing spaces
       time_str = time_str.strip()
       
       # Replace comma with period
       time_str = time_str.replace(',', '.')
       
       # Parse components
       parts = time_str.split(':')
       if len(parts) == 3:
           hours = int(parts[0])
           minutes = int(parts[1])
           seconds_parts = parts[2].split('.')
           seconds = int(seconds_parts[0])
           milliseconds = int(seconds_parts[1][:2]) if len(seconds_parts) > 1 else 0
           
           # ASS format: H:MM:SS.cc (cc = centiseconds)
           centiseconds = milliseconds // 10
           return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
       
       return time_str


# Singleton instance
srt_service = SrtService()

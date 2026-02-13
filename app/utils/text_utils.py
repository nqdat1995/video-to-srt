"""Text processing utilities"""

import re
from difflib import SequenceMatcher


def srt_timestamp(seconds: float) -> str:
   """
   Convert seconds to SRT timestamp format (HH:MM:SS,mmm)

   Args:
       seconds: Time in seconds

   Returns:
       Formatted timestamp string
   """
   if seconds < 0:
       seconds = 0.0
   ms = int(round(seconds * 1000))
   hh = ms // 3600000
   ms -= hh * 3600000
   mm = ms // 60000
   ms -= mm * 60000
   ss = ms // 1000
   ms -= ss * 1000
   return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def normalize_text(s: str) -> str:
   """
   Normalize text by removing extra whitespace and zero-width characters

   Args:
       s: Input text

   Returns:
       Normalized text
   """
   s = s.replace("\u200b", "").strip()
   # collapse whitespace but preserve line breaks
   lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.split("\n")]
   lines = [ln for ln in lines if ln]
   return "\n".join(lines)


def strip_quotes(s: str) -> str:
   """
   Strip leading/trailing single and double quotes from text
   
   Handles cases where OCR sometimes returns quoted text and sometimes doesn't,
   ensuring that "text" and 'text' and text are treated as equivalent.

   Args:
       s: Input text

   Returns:
       Text with quotes stripped
   """
   s = s.strip()
   # Strip leading/trailing single quotes
   if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
       s = s[1:-1]
   # Strip leading/trailing double quotes
   if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
       s = s[1:-1]
   # Strip mixed quotes (e.g., "text' → text)
   while s and s[0] in ("'", '"'):
       s = s[1:]
   while s and s[-1] in ("'", '"'):
       s = s[:-1]
   return s


def similarity(a: str, b: str) -> float:
   """
   Calculate similarity ratio between two strings
   
   Strips quotes before comparison to handle OCR variance where quotes
   may or may not be present (e.g., "text" vs text).

   Args:
       a: First string
       b: Second string

   Returns:
       Similarity ratio from 0.0 to 1.0
   """
   a_clean = strip_quotes(a)
   b_clean = strip_quotes(b)
   return SequenceMatcher(None, a_clean, b_clean).ratio()

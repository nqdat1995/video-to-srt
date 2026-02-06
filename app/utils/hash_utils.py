"""Hash-based utilities for frame comparison"""

import cv2
import numpy as np


def ahash(gray: np.ndarray, size: int = 8) -> int:
   """
   Calculate average hash (aHash) for grayscale image

   Args:
       gray: Grayscale image
       size: Hash size (default 8x8)

   Returns:
       Integer hash value
   """
   small = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA)
   avg = float(small.mean())
   bits = (small > avg).astype(np.uint8).flatten()
   h = 0
   for bit in bits:
       h = (h << 1) | int(bit)
   return h


def hamming64(a: int, b: int) -> int:
   """
   Calculate Hamming distance between two hash values

   Args:
       a: First hash
       b: Second hash

   Returns:
       Number of different bits
   """
   return (a ^ b).bit_count()

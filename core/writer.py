"""
core/writer.py
--------------
VideoWriter wrapper for surf-pal output files.

Manages two optional ``cv2.VideoWriter`` instances:
  • **Main output** – the zoomed virtual-camera crop saved to ``tmp/output.mp4``.
  • **Debug output** – the full-resolution annotated frame saved to
    ``tmp/output_debug.mp4`` (only created when ``debug_path`` is supplied).
"""

from __future__ import annotations
from typing import Optional, Tuple
import cv2
import numpy as np


class VideoOutputWriter:
    """
    Thin wrapper around ``cv2.VideoWriter`` that manages the main and optional
    debug output video files.

    Args:
        path:        Path for the virtual-camera (cropped) output video.
        fps:         Frames per second for the output video.
        crop_size:   ``(width, height)`` of the cropped virtual-camera frames.
        debug_path:  Optional path for the full-resolution debug video.
                     Pass ``None`` to skip the debug writer entirely.
        frame_size:  ``(width, height)`` of the full-resolution frames,
                     required when *debug_path* is not ``None``.
    """

    _FOURCC = cv2.VideoWriter_fourcc(*"mp4v")  # H.264-compatible MP4 container

    def __init__(
        self,
        path: str,
        fps: float,
        crop_size: Tuple[int, int],
        debug_path: Optional[str] = None,
        frame_size: Optional[Tuple[int, int]] = None,
    ) -> None:
        # Main output — always created
        self._main = cv2.VideoWriter(path, self._FOURCC, fps, crop_size)

        # Debug output — only created when a path is provided
        self._debug: Optional[cv2.VideoWriter] = None
        if debug_path is not None:
            if frame_size is None:
                raise ValueError(
                    "frame_size must be provided when debug_path is set."
                )
            self._debug = cv2.VideoWriter(
                debug_path, self._FOURCC, fps, frame_size
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write(
        self,
        crop_frame: np.ndarray,
        debug_frame: Optional[np.ndarray] = None,
    ) -> None:
        """
        Write one frame to each active writer.

        Args:
            crop_frame:  Zoomed virtual-camera frame (always written).
            debug_frame: Full-resolution annotated frame; written only when
                         the debug writer is active and this argument is not None.
        """
        self._main.write(crop_frame)

        if self._debug is not None and debug_frame is not None:
            self._debug.write(debug_frame)

    def release(self) -> None:
        """Flush and close all open video writers."""
        self._main.release()
        if self._debug is not None:
            self._debug.release()

    @property
    def has_debug(self) -> bool:
        """``True`` when a debug video writer is active."""
        return self._debug is not None

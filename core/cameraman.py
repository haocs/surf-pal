"""
core/cameraman.py
-----------------
Virtual camera with exponential smoothing for surf-pal.

Simulates a physical cameraman panning to follow a subject by maintaining a
crop rectangle that smoothly tracks the target's bounding-box centre.
Exponential moving average (EMA) smoothing prevents jarring jumps when the
target moves quickly or briefly disappears.
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class Cameraman:
    """
    Virtual camera that zooms into and follows a target within a larger frame.

    The camera maintains a crop window of size ``(src_w / zoom, src_h / zoom)``
    and smoothly pans it toward the target's centre using an exponential moving
    average:

        new_center = (1 - α) * old_center + α * target_center

    A small ``α`` (e.g. 0.05) gives very smooth but slow panning; a large ``α``
    (e.g. 0.3) tracks quickly but can look jittery.

    Args:
        source_width:     Full-resolution frame width in pixels.
        source_height:    Full-resolution frame height in pixels.
        zoom_level:       Zoom factor (e.g. ``2.0`` → crop is half the frame).
        smoothing_factor: EMA smoothing coefficient ``α ∈ (0, 1]``.
    """

    def __init__(
        self,
        source_width: int,
        source_height: int,
        zoom_level: float = 2.0,
        smoothing_factor: float = 0.1,
    ) -> None:
        self.src_w = source_width
        self.src_h = source_height
        self.zoom = zoom_level
        self.alpha = smoothing_factor

        # Derived crop dimensions (fixed throughout the session)
        self.crop_w = int(self.src_w / self.zoom)
        self.crop_h = int(self.src_h / self.zoom)

        # Start the virtual camera centred on the frame
        self.current_center_x: float = self.src_w / 2
        self.current_center_y: float = self.src_h / 2

    def update(
        self, target_bbox: Optional[np.ndarray]
    ) -> Tuple[int, int, int, int]:
        """
        Advance the virtual camera position for one frame.

        If *target_bbox* is provided the camera pans toward the target centre;
        otherwise it stays at its current position (no drift-back, avoids
        disorienting motion when tracking is temporarily lost).

        Args:
            target_bbox: ``[x1, y1, x2, y2]`` bounding box of the target,
                         or ``None`` when the target is not detected.

        Returns:
            ``(x, y, crop_w, crop_h)`` — top-left origin and size of the
            crop rectangle, clamped so it never extends outside the frame.
        """
        if target_bbox is not None:
            x1, y1, x2, y2 = target_bbox
            target_cx = (x1 + x2) / 2
            target_cy = (y1 + y2) / 2
        else:
            # Target lost — hold the current position (no drift)
            target_cx = self.current_center_x
            target_cy = self.current_center_y

        # Exponential moving average smooths panning motion
        self.current_center_x = (
            (1 - self.alpha) * self.current_center_x + self.alpha * target_cx
        )
        self.current_center_y = (
            (1 - self.alpha) * self.current_center_y + self.alpha * target_cy
        )

        # Convert smoothed centre to a top-left crop origin
        x_start = int(self.current_center_x - self.crop_w / 2)
        y_start = int(self.current_center_y - self.crop_h / 2)

        # Clamp so the crop window never goes outside the frame boundaries
        x_start = max(0, min(x_start, self.src_w - self.crop_w))
        y_start = max(0, min(y_start, self.src_h - self.crop_h))

        return x_start, y_start, self.crop_w, self.crop_h

    def crop(self, frame: np.ndarray, crop_rect: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Slice *frame* to the crop rectangle returned by :meth:`update`.

        Args:
            frame:     Full-resolution BGR frame.
            crop_rect: ``(x, y, w, h)`` from :meth:`update`.

        Returns:
            Cropped BGR sub-image of size ``(crop_h, crop_w)``.
        """
        x, y, w, h = crop_rect
        return frame[y : y + h, x : x + w]

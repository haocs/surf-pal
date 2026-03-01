"""
core/cameraman.py
-----------------
Virtual camera with exponential smoothing and dynamic zoom for surf-pal.

Simulates a physical cameraman panning to follow a subject by maintaining a
crop rectangle that smoothly tracks the target's bounding-box centre.
Exponential moving average (EMA) smoothing prevents jarring jumps when the
target moves quickly or briefly disappears.

The zoom level can be changed per-frame via :meth:`set_zoom`.  The output
crop is always resized to the **base** crop dimensions (computed from the
initial zoom) so downstream consumers (VideoWriter, display) see a constant
frame size.
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class Cameraman:
    """
    Virtual camera that zooms into and follows a target within a larger frame.

    The camera maintains a crop window whose size is derived from the current
    zoom level, and smoothly pans it toward the target's centre using an
    exponential moving average:

        new_center = (1 - α) * old_center + α * target_center

    A small ``α`` (e.g. 0.05) gives very smooth but slow panning; a large ``α``
    (e.g. 0.3) tracks quickly but can look jittery.

    Args:
        source_width:     Full-resolution frame width in pixels.
        source_height:    Full-resolution frame height in pixels.
        zoom_level:       Initial zoom factor (e.g. ``2.0`` → crop is half the
                          frame).  Can be changed at runtime via :meth:`set_zoom`.
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
        self.alpha = smoothing_factor

        # --- Base (output) dimensions — fixed for the lifetime of the session
        # These define the VideoWriter frame size and are derived from the
        # initial zoom level.
        self._base_zoom = zoom_level
        self.crop_w = int(self.src_w / self._base_zoom)
        self.crop_h = int(self.src_h / self._base_zoom)

        # --- Dynamic zoom — may differ from base zoom each frame
        self._zoom: float = zoom_level

        # Start the virtual camera centred on the frame
        self.current_center_x: float = self.src_w / 2
        self.current_center_y: float = self.src_h / 2

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_zoom(self, zoom_level: float) -> None:
        """
        Change the zoom level for the next :meth:`update` call.

        The output crop is always resized to the base dimensions
        (``self.crop_w × self.crop_h``) so downstream consumers are unaffected.

        Args:
            zoom_level: New zoom factor (≥ 1.0).
        """
        self._zoom = max(1.0, zoom_level)

    @property
    def zoom(self) -> float:
        """Current dynamic zoom level."""
        return self._zoom

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
            ``(x, y, w, h)`` — top-left origin and size of the *actual* crop
            rectangle (which may differ from ``crop_w × crop_h`` when dynamic
            zoom is active), clamped so it never extends outside the frame.
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

        # Compute the dynamic crop dimensions from the current zoom
        dyn_crop_w = int(self.src_w / self._zoom)
        dyn_crop_h = int(self.src_h / self._zoom)

        # Convert smoothed centre to a top-left crop origin
        x_start = int(self.current_center_x - dyn_crop_w / 2)
        y_start = int(self.current_center_y - dyn_crop_h / 2)

        # Clamp so the crop window never goes outside the frame boundaries
        x_start = max(0, min(x_start, self.src_w - dyn_crop_w))
        y_start = max(0, min(y_start, self.src_h - dyn_crop_h))

        return x_start, y_start, dyn_crop_w, dyn_crop_h

    def crop(
        self, frame: np.ndarray, crop_rect: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """
        Slice *frame* to the crop rectangle and resize to the fixed base
        dimensions so the output size is constant regardless of zoom level.

        Args:
            frame:     Full-resolution BGR frame.
            crop_rect: ``(x, y, w, h)`` from :meth:`update`.

        Returns:
            BGR sub-image resized to ``(self.crop_w, self.crop_h)``.
        """
        x, y, w, h = crop_rect
        cropped = frame[y : y + h, x : x + w]

        # Resize to constant output dimensions when dynamic zoom differs
        if w != self.crop_w or h != self.crop_h:
            cropped = cv2.resize(
                cropped, (self.crop_w, self.crop_h), interpolation=cv2.INTER_LINEAR
            )

        return cropped

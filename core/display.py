"""
core/display.py
---------------
OpenCV-based rendering and windowing for the surf-pal debug view.

Responsibilities:
  • Compositing detection overlays on the full-resolution frame.
  • Drawing the virtual-camera crop rectangle.
  • Optionally drawing the locked-target bounding box and status text.
  • Downscaling the debug frame to fit 1080p monitors.
  • Showing the World View and Virtual Camera windows.
"""

from __future__ import annotations
from typing import Optional, Tuple
import cv2
import numpy as np


# Maximum display width — frames wider than this are scaled down for viewing
_MAX_DISPLAY_WIDTH = 1920


class Display:
    """
    Handles all rendering and window management for the debug view.

    Args:
        frame_height:    Full-resolution frame height (pixels).
        debug_tracking:  When True, draw the target bounding box and
                         TRACKING/LOST status text on the debug frame.
    """

    def __init__(self, frame_height: int, debug_tracking: bool = False) -> None:
        self.frame_height = frame_height
        self.debug_tracking = debug_tracking

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(
        self,
        frame: np.ndarray,
        results,
        crop_rect: Tuple[int, int, int, int],
        target_box: Optional[np.ndarray],
        locked_track_id: Optional[int],
    ) -> np.ndarray:
        """
        Build the full-resolution debug frame for this iteration.

        Steps:
          1. Plot all YOLO detections (bounding boxes + labels).
          2. Draw the virtual-camera crop window in cyan.
          3. If debug_tracking is enabled, overlay the target box and
             a status text string.

        Args:
            frame:           Raw BGR frame from the video source.
            results:         YOLO Results object for this frame.
            crop_rect:       ``(x, y, w, h)`` of the current crop window.
            target_box:      ``[x1, y1, x2, y2]`` of the locked target, or None.
            locked_track_id: Current locked track ID, or None.

        Returns:
            Annotated BGR frame at full resolution.
        """
        x, y, crop_w, crop_h = crop_rect

        # --- Step 1: overlay YOLO detections on a copy of the frame ---
        if results.boxes is not None:
            # results.plot() returns a new annotated frame; no need to copy again
            debug_frame = results.plot()
        else:
            debug_frame = frame.copy()

        # --- Step 2: draw the virtual-camera crop window in cyan ---
        cv2.rectangle(
            debug_frame,
            (x, y),
            (x + crop_w, y + crop_h),
            color=(0, 255, 255),  # cyan
            thickness=4,
        )

        # --- Step 3: optional target-specific overlay ---
        if self.debug_tracking:
            self._draw_target_overlay(debug_frame, target_box, locked_track_id)

        return debug_frame

    def show(self, debug_frame: np.ndarray, cropped_view: np.ndarray) -> None:
        """
        Display the debug frame and the virtual-camera crop in named windows.

        The debug frame is scaled down to fit the screen if wider than
        ``_MAX_DISPLAY_WIDTH``.

        Args:
            debug_frame:   Full-resolution annotated frame.
            cropped_view:  Zoomed-in virtual camera output.
        """
        scaled = self._scale_for_screen(debug_frame)
        cv2.imshow("World View", scaled)
        cv2.imshow("Virtual Camera", cropped_view)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _draw_target_overlay(
        self,
        frame: np.ndarray,
        target_box: Optional[np.ndarray],
        locked_track_id: Optional[int],
    ) -> None:
        """
        Draw the target bounding box and a TRACKING/LOST status string
        at the bottom-left corner of the frame (in-place).
        """
        ui_x = 30
        ui_y = self.frame_height - 30  # bottom-left anchor

        if target_box is not None:
            # Green box around the locked surfer
            tx1, ty1, tx2, ty2 = map(int, target_box)
            cv2.rectangle(frame, (tx1, ty1), (tx2, ty2), (0, 255, 0), 2)

            text = f"TRACKING ID: {locked_track_id}"
            cv2.putText(
                frame, text, (ui_x, ui_y),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2,
            )
        elif locked_track_id is not None:
            # Red text when the previously-locked target is temporarily lost
            text = f"LOST ID: {locked_track_id}"
            cv2.putText(
                frame, text, (ui_x, ui_y),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2,
            )

    def _scale_for_screen(self, frame: np.ndarray) -> np.ndarray:
        """
        Proportionally scale *frame* so it fits within ``_MAX_DISPLAY_WIDTH``
        columns.  Returns the original frame unchanged if it is already small
        enough (e.g. 1080p source).
        """
        h, w = frame.shape[:2]
        if w > _MAX_DISPLAY_WIDTH:
            scale = _MAX_DISPLAY_WIDTH / w
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
        return frame

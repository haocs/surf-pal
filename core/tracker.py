"""
core/tracker.py
---------------
Target selection and ID-lock logic for the surf-pal camera system.

The Tracker maintains a "locked" track ID so the virtual camera follows a
single surfer across frames.  When the locked target disappears it falls back
to the largest detected person and re-locks on them.
"""

from __future__ import annotations
from typing import Optional, Tuple
import numpy as np


class Tracker:
    """
    Selects and locks onto a single person across YOLO tracking frames.

    Attributes:
        locked_track_id: The track ID currently being followed, or None.
        prev_visible:    Whether the target was visible in the previous frame.
        prev_locked_id:  The locked ID from the previous frame (used to detect
                         switches for event logging).
    """

    def __init__(self) -> None:
        self.locked_track_id: Optional[int] = None
        self.prev_visible: bool = False
        self.prev_locked_id: Optional[int] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self, results
    ) -> Tuple[Optional[np.ndarray], Optional[int], Optional[int]]:
        """
        Parse one frame's YOLO results and return the selected target.

        Strategy:
          1. If a track ID is already locked and still present → follow it.
          2. Otherwise → pick the largest detected person and lock onto them.

        Args:
            results: A single YOLO ``Results`` object (``model.track(...)[0]``).

        Returns:
            A 3-tuple ``(target_box, current_track_id, prev_locked_id)`` where:

            * ``target_box``      – ``[x1, y1, x2, y2]`` array or ``None``.
            * ``current_track_id``– Track ID of the chosen target, or ``None``.
            * ``prev_locked_id``  – The locked ID *before* this update (used by
                                    EventLogger to detect ID switches).
        """
        # Remember last frame's lock so the caller can detect changes
        self.prev_locked_id = self.locked_track_id

        # Parse all detections into {track_id: bbox} and find the largest person
        detections, largest_person_id, largest_person_box = self._parse_results(results)

        target_box, current_track_id = self._select_target(
            detections, largest_person_id, largest_person_box
        )

        # Update visibility state for next frame
        self.prev_visible = target_box is not None

        return target_box, current_track_id, self.prev_locked_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_results(self, results):
        """
        Extract person detections from a YOLO Results object.

        Returns:
            detections         – dict mapping track_id → bbox array.
            largest_person_id  – track_id of the person with the largest area.
            largest_person_box – bbox of that person.
        """
        detections: dict[int, np.ndarray] = {}
        max_area = 0
        largest_person_id: Optional[int] = None
        largest_person_box: Optional[np.ndarray] = None

        if results.boxes is None:
            return detections, largest_person_id, largest_person_box

        for box in results.boxes:
            cls = int(box.cls[0])

            # Class 0 = person in the COCO dataset used by YOLOv8
            if cls != 0:
                continue

            coords: np.ndarray = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = coords
            area = (x2 - x1) * (y2 - y1)

            track_id: Optional[int] = int(box.id[0]) if box.id is not None else None

            if track_id is not None:
                detections[track_id] = coords

            if area > max_area:
                max_area = area
                largest_person_box = coords
                largest_person_id = track_id

        return detections, largest_person_id, largest_person_box

    def _select_target(self, detections, largest_person_id, largest_person_box):
        """
        Apply the lock-or-fallback strategy to choose the target this frame.

        Returns:
            (target_box, current_track_id)
        """
        # Priority 1: re-find the already-locked target
        if self.locked_track_id is not None and self.locked_track_id in detections:
            return detections[self.locked_track_id], self.locked_track_id

        # Priority 2: fall back to the largest visible person and re-lock
        if largest_person_box is not None:
            self.locked_track_id = largest_person_id
            return largest_person_box, largest_person_id

        # No person detected at all
        return None, None

"""
core/tracking/largest_person.py
-------------------------------
Default tracking strategy: lock onto the largest detected person.

This is the original surf-pal behaviour extracted into a strategy object that
satisfies :class:`~core.tracking.base.TrackingStrategy`.

Strategy:
  1. If a track ID is already locked and still present → keep following it.
  2. Otherwise → fall back to the largest detected person and re-lock.
"""

from __future__ import annotations
from typing import Optional, Dict
import numpy as np

from core.tracking.base import TrackingResult


class LargestPersonStrategy:
    """
    Tracking strategy that locks onto the biggest person bounding box.

    Attributes:
        locked_track_id: The track ID currently being followed, or ``None``.
    """

    def __init__(self) -> None:
        self.locked_track_id: Optional[int] = None
        self._prev_locked_id: Optional[int] = None

    # ------------------------------------------------------------------
    # TrackingStrategy interface
    # ------------------------------------------------------------------

    def update(self, results) -> TrackingResult:
        """
        Parse YOLO results and apply the lock-or-fallback selection strategy.

        Args:
            results: A single YOLO ``Results`` object.

        Returns:
            :class:`TrackingResult` carrying the selected target box and IDs.
        """
        # Snapshot the previous lock before we potentially change it
        self._prev_locked_id = self.locked_track_id

        # Parse detections
        detections, largest_id, largest_box = self._parse_results(results)

        # Select target
        target_box, track_id = self._select_target(
            detections, largest_id, largest_box
        )

        return TrackingResult(
            target_box=target_box,
            track_id=track_id,
            prev_id=self._prev_locked_id,
            metadata={},
        )

    def reset(self) -> None:
        """Clear the locked target and start fresh."""
        self.locked_track_id = None
        self._prev_locked_id = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_results(self, results):
        """
        Extract person (class 0) detections from YOLO results.

        Returns:
            detections         – ``{track_id: bbox_array}``
            largest_person_id  – ID of the person with the largest bbox area.
            largest_person_box – Corresponding bbox array.
        """
        detections: Dict[int, np.ndarray] = {}
        max_area = 0
        largest_person_id: Optional[int] = None
        largest_person_box: Optional[np.ndarray] = None

        if results.boxes is None:
            return detections, largest_person_id, largest_person_box

        for box in results.boxes:
            cls = int(box.cls[0])
            if cls != 0:  # 0 = person in COCO
                continue

            coords: np.ndarray = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = coords
            area = (x2 - x1) * (y2 - y1)

            track_id: Optional[int] = (
                int(box.id[0]) if box.id is not None else None
            )

            if track_id is not None:
                detections[track_id] = coords

            if area > max_area:
                max_area = area
                largest_person_box = coords
                largest_person_id = track_id

        return detections, largest_person_id, largest_person_box

    def _select_target(self, detections, largest_id, largest_box):
        """
        Apply lock-or-fallback to pick this frame's target.

        Returns:
            ``(target_box, track_id)``
        """
        # Priority 1: follow the locked target if still visible
        if self.locked_track_id is not None and self.locked_track_id in detections:
            return detections[self.locked_track_id], self.locked_track_id

        # Priority 2: re-lock onto the largest person
        if largest_box is not None:
            self.locked_track_id = largest_id
            return largest_box, largest_id

        # No person detected
        return None, None

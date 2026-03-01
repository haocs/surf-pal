"""
core/activity.py
----------------
Heuristic activity classifier for surf tracking.

Classifies the surfer's current activity based on cheap motion signals
extracted from the bounding box across frames — no additional ML model
required.

Signals used
~~~~~~~~~~~~
* **Horizontal speed** — large Δx across a sliding window → RIDING.
* **Vertical position** — low in the frame → likely on a wave face.
* **Bbox aspect ratio** — tall & narrow (standing) → RIDING; wide & short
  (prone) → PADDLING.
"""

from __future__ import annotations
from collections import deque
from enum import Enum
from typing import Optional
import numpy as np


class Activity(Enum):
    """Discrete activity states that drive the zoom controller."""
    RIDING = "riding"      # On a wave — want tight zoom
    PADDLING = "paddling"  # Moving through water — medium zoom
    SITTING = "sitting"    # Waiting in the lineup — wide zoom
    UNKNOWN = "unknown"    # Not enough data yet


# ---------------------------------------------------------------------------
# Tuning constants — tweak these for different camera distances / resolutions
# ---------------------------------------------------------------------------

# Minimum horizontal speed (pixels / frame) to be considered "riding"
_RIDING_SPEED_THRESHOLD = 8.0

# Minimum horizontal speed to be considered "paddling" (below this → sitting)
_PADDLING_SPEED_THRESHOLD = 2.0

# Aspect ratio (width / height) below which the person is likely standing up
_STANDING_ASPECT_RATIO = 0.55

# Number of recent frames to average over (smooths single-frame noise)
_HISTORY_LENGTH = 10


class ActivityClassifier:
    """
    Classify the surfer's activity using bounding-box motion heuristics.

    The classifier maintains a short rolling window of bbox centres and
    aspect ratios.  On each call to :meth:`update` it computes the average
    horizontal speed and aspect ratio over that window, then applies simple
    threshold rules.

    Args:
        history_length: Number of frames to keep in the sliding window.
    """

    def __init__(self, history_length: int = _HISTORY_LENGTH) -> None:
        # Rolling buffers for smoothing
        self._cx_history: deque[float] = deque(maxlen=history_length)
        self._ar_history: deque[float] = deque(maxlen=history_length)

        self._current: Activity = Activity.UNKNOWN

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        target_box: Optional[np.ndarray],
        frame_height: int,
    ) -> Activity:
        """
        Classify the surfer's activity for this frame.

        Args:
            target_box:   ``[x1, y1, x2, y2]`` of the target, or ``None``.
            frame_height: Height of the source frame in pixels (used to
                          normalise vertical position).

        Returns:
            The classified :class:`Activity`.
        """
        if target_box is None:
            # Can't classify without a detection — keep last known state
            return self._current

        x1, y1, x2, y2 = target_box
        cx = (x1 + x2) / 2.0
        box_w = x2 - x1
        box_h = max(y2 - y1, 1)  # avoid division by zero

        # Record the current centre-x and aspect ratio
        self._cx_history.append(cx)
        self._ar_history.append(box_w / box_h)

        # Need at least 2 data points to compute speed
        if len(self._cx_history) < 2:
            return Activity.UNKNOWN

        self._current = self._classify()
        return self._current

    def reset(self) -> None:
        """Clear the history buffers and return to UNKNOWN."""
        self._cx_history.clear()
        self._ar_history.clear()
        self._current = Activity.UNKNOWN

    @property
    def current(self) -> Activity:
        """Most recently classified activity."""
        return self._current

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify(self) -> Activity:
        """
        Apply threshold rules to the averaged motion signals.

        Decision tree:
          1. Fast horizontal movement + standing aspect → RIDING
          2. Moderate movement → PADDLING
          3. Slow / no movement → SITTING
        """
        # Average absolute horizontal speed over the window (pixels / frame)
        speeds = [
            abs(self._cx_history[i] - self._cx_history[i - 1])
            for i in range(1, len(self._cx_history))
        ]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0

        # Average aspect ratio (width / height) over the window
        avg_ar = sum(self._ar_history) / len(self._ar_history)

        # --- Decision rules ---

        # High speed + upright posture → very likely riding a wave
        if avg_speed >= _RIDING_SPEED_THRESHOLD and avg_ar <= _STANDING_ASPECT_RATIO:
            return Activity.RIDING

        # High speed alone (even without standing posture) still likely riding
        if avg_speed >= _RIDING_SPEED_THRESHOLD:
            return Activity.RIDING

        # Moderate speed → paddling
        if avg_speed >= _PADDLING_SPEED_THRESHOLD:
            return Activity.PADDLING

        # Low speed → sitting / waiting in the lineup
        return Activity.SITTING

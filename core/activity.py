"""
core/activity.py
----------------
Heuristic activity classifier for surf tracking.

Classifies the surfer's current activity based on cheap motion signals
extracted from the bounding box across frames — no additional ML model
required.

Signals used
~~~~~~~~~~~~
* **2D speed** — total displacement per frame (√(Δx² + Δy²)) → RIDING.
* **Vertical speed** — dropping on a wave face is a strong riding signal.
* **Bbox area variance** — rapid area changes (compression, stance shifts)
  indicate active riding.
* **Bbox aspect ratio** — tall & narrow (standing) → RIDING support.
* **State stickiness** — once RIDING is classified, hold for a minimum
  number of frames to avoid flicker from momentary compressions.
"""

from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import math
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

# Minimum 2D speed (pixels / frame) to be considered "riding"
_RIDING_SPEED_THRESHOLD = 6.0

# Minimum vertical speed (pixels / frame) that alone suggests riding
# (surfer dropping down a wave face)
_VERTICAL_RIDING_THRESHOLD = 4.0

# Minimum 2D speed to be considered "paddling" (below this → sitting)
_PADDLING_SPEED_THRESHOLD = 2.0

# A moderate speed combined with high area variance → likely riding
_MODERATE_SPEED_THRESHOLD = 3.5

# Coefficient of variation of bbox area above which body is actively changing
_AREA_VARIANCE_THRESHOLD = 0.05

# Aspect ratio (width / height) below which the person is likely standing up
_STANDING_ASPECT_RATIO = 0.55

# Number of recent frames to average over (smooths single-frame noise)
_HISTORY_LENGTH = 10

# Once RIDING is classified, hold it for at least this many frames (~0.5s @30fps)
_RIDING_HOLD_FRAMES = 15


@dataclass
class ClassifierSignals:
    """Raw signal values from the most recent classification — useful for debug."""
    total_speed: float = 0.0
    vert_speed: float = 0.0
    area_cv: float = 0.0
    avg_ar: float = 0.0


class ActivityClassifier:
    """
    Classify the surfer's activity using bounding-box motion heuristics.

    The classifier maintains a short rolling window of bbox centres, aspect
    ratios, and areas.  On each call to :meth:`update` it computes 2D speed,
    vertical speed, area variance, and aspect ratio over that window, then
    applies threshold rules with state stickiness.

    Args:
        history_length: Number of frames to keep in the sliding window.
    """

    def __init__(self, history_length: int = _HISTORY_LENGTH) -> None:
        # Rolling buffers for smoothing
        self._cx_history: deque[float] = deque(maxlen=history_length)
        self._cy_history: deque[float] = deque(maxlen=history_length)
        self._ar_history: deque[float] = deque(maxlen=history_length)
        self._area_history: deque[float] = deque(maxlen=history_length)

        self._current: Activity = Activity.UNKNOWN
        self._riding_hold_counter: int = 0

        # Expose the most recent raw signals for debug overlay
        self.signals = ClassifierSignals()

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
            self._tick_hold()
            return self._current

        x1, y1, x2, y2 = target_box
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        box_w = x2 - x1
        box_h = max(y2 - y1, 1)  # avoid division by zero
        area = box_w * box_h

        # Record current measurements
        self._cx_history.append(cx)
        self._cy_history.append(cy)
        self._ar_history.append(box_w / box_h)
        self._area_history.append(area)

        # Need at least 2 data points to compute speed
        if len(self._cx_history) < 2:
            return Activity.UNKNOWN

        self._current = self._classify()
        return self._current

    def reset(self) -> None:
        """Clear the history buffers and return to UNKNOWN."""
        self._cx_history.clear()
        self._cy_history.clear()
        self._ar_history.clear()
        self._area_history.clear()
        self._current = Activity.UNKNOWN
        self._riding_hold_counter = 0
        self.signals = ClassifierSignals()

    @property
    def current(self) -> Activity:
        """Most recently classified activity."""
        return self._current

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _tick_hold(self) -> None:
        """Decrement the riding hold counter if active."""
        if self._riding_hold_counter > 0:
            self._riding_hold_counter -= 1

    def _classify(self) -> Activity:
        """
        Apply threshold rules to multiple motion signals.

        Decision logic:
          1. High 2D speed → RIDING
          2. Significant vertical speed (wave-face drop) → RIDING
          3. Moderate speed + high area variance (active body) → RIDING
          4. Currently in RIDING hold window → stay RIDING (stickiness)
          5. Moderate speed → PADDLING
          6. Low speed → SITTING
        """
        n = len(self._cx_history)

        # --- 2D speed: average Euclidean displacement per frame ---
        speeds_2d = [
            math.sqrt(
                (self._cx_history[i] - self._cx_history[i - 1]) ** 2
                + (self._cy_history[i] - self._cy_history[i - 1]) ** 2
            )
            for i in range(1, n)
        ]
        total_speed = sum(speeds_2d) / len(speeds_2d) if speeds_2d else 0.0

        # --- Vertical speed: average absolute Δcy per frame ---
        vert_speeds = [
            abs(self._cy_history[i] - self._cy_history[i - 1])
            for i in range(1, n)
        ]
        vert_speed = sum(vert_speeds) / len(vert_speeds) if vert_speeds else 0.0

        # --- Bbox area coefficient of variation (std / mean) ---
        areas = list(self._area_history)
        mean_area = sum(areas) / len(areas)
        if mean_area > 0:
            area_var = math.sqrt(
                sum((a - mean_area) ** 2 for a in areas) / len(areas)
            ) / mean_area
        else:
            area_var = 0.0

        # --- Average aspect ratio (width / height) ---
        avg_ar = sum(self._ar_history) / len(self._ar_history)

        # Store signals for debug overlay
        self.signals = ClassifierSignals(
            total_speed=total_speed,
            vert_speed=vert_speed,
            area_cv=area_var,
            avg_ar=avg_ar,
        )

        # --- Decision rules ---

        # Rule 1: Fast 2D movement → RIDING
        if total_speed >= _RIDING_SPEED_THRESHOLD:
            self._riding_hold_counter = _RIDING_HOLD_FRAMES
            return Activity.RIDING

        # Rule 2: Significant vertical movement → RIDING (wave face drop)
        if vert_speed >= _VERTICAL_RIDING_THRESHOLD:
            self._riding_hold_counter = _RIDING_HOLD_FRAMES
            return Activity.RIDING

        # Rule 3: Moderate speed + high area variance → RIDING
        if (total_speed >= _MODERATE_SPEED_THRESHOLD
                and area_var >= _AREA_VARIANCE_THRESHOLD):
            self._riding_hold_counter = _RIDING_HOLD_FRAMES
            return Activity.RIDING

        # Rule 4: Stickiness — hold RIDING classification
        if self._riding_hold_counter > 0:
            self._riding_hold_counter -= 1
            return Activity.RIDING

        # Rule 5: Moderate speed → PADDLING
        if total_speed >= _PADDLING_SPEED_THRESHOLD:
            return Activity.PADDLING

        # Rule 6: Low speed → SITTING
        return Activity.SITTING

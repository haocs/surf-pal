"""
core/zoom_controller.py
-----------------------
Activity-aware dynamic zoom controller for surf-pal.

Maps the surfer's classified activity to a target zoom level and applies
EMA smoothing so the virtual camera never jumps abruptly from wide to tight
framing (or vice-versa).
"""

from __future__ import annotations
from typing import Dict, Optional
from core.activity import Activity


# Default zoom presets per activity
_DEFAULT_PRESETS: Dict[Activity, float] = {
    Activity.RIDING: 3.0,     # Tight — emphasise turns and spray
    Activity.PADDLING: 2.0,   # Medium — show the surfer and some context
    Activity.SITTING: 1.5,    # Wide — lineup context while waiting
    Activity.UNKNOWN: 2.0,    # Safe fallback
}


class ZoomController:
    """
    Smooth, activity-driven zoom level.

    Each frame, :meth:`update` receives the current :class:`Activity` and
    returns a smoothed zoom value suitable for passing to
    :meth:`Cameraman.set_zoom`.

    Args:
        presets:    Mapping of ``Activity → target zoom``.
                    Defaults to :data:`_DEFAULT_PRESETS`.
        smoothing:  EMA coefficient ``α ∈ (0, 1]``.  Smaller values give
                    slower, smoother zoom transitions.
        min_zoom:   Floor clamp — zoom never goes below this value.
        max_zoom:   Ceiling clamp — zoom never exceeds this value.
    """

    def __init__(
        self,
        presets: Optional[Dict[Activity, float]] = None,
        smoothing: float = 0.05,
        min_zoom: float = 1.0,
        max_zoom: float = 4.0,
    ) -> None:
        self.presets = presets or dict(_DEFAULT_PRESETS)
        self.alpha = smoothing
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom

        # Start at a neutral zoom; first update will begin converging
        self._current_zoom: float = self.presets.get(Activity.UNKNOWN, 2.0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, activity: Activity) -> float:
        """
        Compute the smoothed zoom for this frame.

        Args:
            activity: The surfer's current activity classification.

        Returns:
            Smoothed zoom level (float), clamped to ``[min_zoom, max_zoom]``.
        """
        target = self.presets.get(activity, self._current_zoom)

        # EMA smoothing: new = (1-α)*old + α*target
        self._current_zoom = (
            (1 - self.alpha) * self._current_zoom + self.alpha * target
        )

        # Clamp to the allowed range
        self._current_zoom = max(self.min_zoom, min(self._current_zoom, self.max_zoom))

        return self._current_zoom

    @property
    def current_zoom(self) -> float:
        """The most recent smoothed zoom value."""
        return self._current_zoom

    def reset(self) -> None:
        """Reset zoom to the UNKNOWN preset."""
        self._current_zoom = self.presets.get(Activity.UNKNOWN, 2.0)

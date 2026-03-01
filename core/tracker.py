"""
core/tracker.py
---------------
Tracker façade for the surf-pal camera system.

This module provides a single entry-point for all tracking operations.
Internally it delegates to a pluggable :class:`TrackingStrategy` so that
the rest of the pipeline (``main.py``, ``EventLogger``, ``Cameraman``, etc.)
never needs to change when you swap in a different tracking mechanism.

Default strategy: :class:`~core.tracking.largest_person.LargestPersonStrategy`.
"""

from __future__ import annotations
from typing import Optional

from core.tracking.base import TrackingStrategy, TrackingResult
from core.tracking.largest_person import LargestPersonStrategy


class Tracker:
    """
    Façade that delegates to one :class:`TrackingStrategy` at a time.

    Args:
        strategy: The tracking strategy to start with.
                  Defaults to :class:`LargestPersonStrategy`.
    """

    def __init__(self, strategy: Optional[TrackingStrategy] = None) -> None:
        self._strategy: TrackingStrategy = strategy or LargestPersonStrategy()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, results) -> TrackingResult:
        """
        Process one frame's YOLO results through the active strategy.

        Args:
            results: A single YOLO ``Results`` object.

        Returns:
            :class:`TrackingResult` with ``target_box``, ``track_id``,
            ``prev_id``, and ``metadata``.
        """
        return self._strategy.update(results)

    def set_strategy(self, strategy: TrackingStrategy) -> None:
        """
        Hot-swap the tracking strategy at runtime.

        The previous strategy's state is discarded.  Call this when the user
        switches from e.g. largest-person mode to color-match or Re-ID mode.

        Args:
            strategy: New strategy instance to use from the next frame onward.
        """
        self._strategy = strategy

    def reset(self) -> None:
        """Reset the active strategy's internal state (e.g. locked IDs)."""
        self._strategy.reset()

    @property
    def strategy_name(self) -> str:
        """Human-readable name of the active strategy (for debug overlay)."""
        return type(self._strategy).__name__

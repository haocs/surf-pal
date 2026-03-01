"""
core/tracking/base.py
---------------------
Defines the abstract interface for tracking strategies.

Any tracking mechanism (largest-person lock, color-based Re-ID, embedding
model, BLE beacon, etc.) implements :class:`TrackingStrategy` so it can be
plugged into the :class:`~core.tracker.Tracker` façade without changing the
rest of the surf-pal pipeline.
"""

from __future__ import annotations
from typing import Optional, Protocol, NamedTuple, Dict, Any
import numpy as np


class TrackingResult(NamedTuple):
    """
    Immutable result returned by every tracking strategy per frame.

    Attributes:
        target_box: ``[x1, y1, x2, y2]`` bounding box of the selected target,
                    or ``None`` when no target is detected.
        track_id:   Integer track ID of the selected target, or ``None``.
        prev_id:    The locked track ID from the *previous* frame.  The
                    :class:`~core.event_logger.EventLogger` uses this to detect
                    ID switches.
        metadata:   Strategy-specific extras (e.g. ``{"confidence": 0.92}``).
                    Safe to ignore if you don't need it.
    """
    target_box: Optional[np.ndarray]
    track_id: Optional[int]
    prev_id: Optional[int]
    metadata: Dict[str, Any]


class TrackingStrategy(Protocol):
    """
    Protocol (structural typing) that every tracking strategy must satisfy.

    Implementors only need to provide two methods — ``update`` and ``reset``.
    No base-class inheritance is required; any object with matching signatures
    is accepted automatically by Python's ``Protocol`` mechanism.
    """

    def update(self, results) -> TrackingResult:
        """
        Process one frame's YOLO results and return the tracking decision.

        Args:
            results: A single ``ultralytics.engine.results.Results`` object.

        Returns:
            A :class:`TrackingResult` with the selected target.
        """
        ...

    def reset(self) -> None:
        """
        Clear all internal state (e.g. locked IDs, history buffers).

        Called when the user wants to re-initialise tracking without
        restarting the entire pipeline.
        """
        ...

"""
core/event_logger.py
--------------------
Records TRACKING and LOST events for the surf-pal debug log.

Events are emitted when:
  • A new track ID is locked (TRACKING).
  • The locked target re-appears after being lost (TRACKING).
  • The locked target disappears (LOST).

All events carry a video timestamp in **milliseconds** derived from the
frame counter and the source video's FPS.
"""

from __future__ import annotations
import json
from typing import Optional


class EventLogger:
    """
    Stateful event recorder that compares current and previous tracking state
    to emit TRACKING / LOST log entries.

    Args:
        fps: Frames-per-second of the source video, used to compute timestamps.
    """

    def __init__(self, fps: float) -> None:
        self.fps = fps
        self._log: list[dict] = []

        # Shadow state from the previous frame
        self._prev_visible: bool = False
        self._prev_locked_id: Optional[int] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        frame_count: int,
        locked_track_id: Optional[int],
        is_visible: bool,
        prev_locked_id: Optional[int],
    ) -> None:
        """
        Evaluate whether an event should be recorded for this frame and append
        it to the internal log if so.

        Args:
            frame_count:     1-based frame index (used with fps for timestamp).
            locked_track_id: The track ID currently locked by the Tracker.
            is_visible:      Whether the target was detected this frame.
            prev_locked_id:  The locked ID from the *previous* frame, so we can
                             detect ID switches (supplied by Tracker).
        """
        timestamp_ms = (frame_count / self.fps) * 1000

        # Case A: The locked ID changed — a new surfer was acquired
        if prev_locked_id != locked_track_id:
            if locked_track_id is not None:
                self._append("TRACKING", locked_track_id, timestamp_ms)

        # Case B: Same ID — check for visibility transitions
        elif locked_track_id is not None:
            if is_visible and not self._prev_visible:
                # Target re-acquired after being lost
                self._append("TRACKING", locked_track_id, timestamp_ms)
            elif not is_visible and self._prev_visible:
                # Target just disappeared
                self._append("LOST", locked_track_id, timestamp_ms)

        # Advance visibility state for the next frame
        self._prev_visible = is_visible
        self._prev_locked_id = locked_track_id

    def save(self, path: str) -> None:
        """
        Persist the event log to a JSON file.

        Args:
            path: File path to write (e.g. ``'tmp/debug_log.json'``).
        """
        with open(path, "w") as f:
            json.dump(self._log, f, indent=2)
        print(f"Debug log saved to {path}")

    @property
    def entries(self) -> list[dict]:
        """Read-only view of the collected log entries."""
        return list(self._log)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append(self, event: str, track_id: int, timestamp_ms: float) -> None:
        """Append a single log entry."""
        self._log.append(
            {
                "timestamp": timestamp_ms,
                "event": event,
                "track_id": track_id,
            }
        )

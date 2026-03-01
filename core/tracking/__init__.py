"""
core/tracking/__init__.py
-------------------------
Re-exports for the tracking sub-package.
"""

from core.tracking.base import TrackingStrategy, TrackingResult
from core.tracking.largest_person import LargestPersonStrategy

__all__ = [
    "TrackingStrategy",
    "TrackingResult",
    "LargestPersonStrategy",
]

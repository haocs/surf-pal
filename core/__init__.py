"""
core/__init__.py
----------------
Convenience re-exports for the surf-pal core package.

Importing from ``core`` directly is preferred over deep imports so that
renaming or reorganising internal files is a one-line change here.
"""

from core.video_loader import VideoLoader
from core.detector import Detector
from core.cameraman import Cameraman
from core.tracker import Tracker
from core.event_logger import EventLogger
from core.display import Display
from core.writer import VideoOutputWriter
from core.activity import Activity, ActivityClassifier
from core.zoom_controller import ZoomController
from core.tracking import TrackingStrategy, TrackingResult, LargestPersonStrategy

__all__ = [
    "VideoLoader",
    "Detector",
    "Cameraman",
    "Tracker",
    "EventLogger",
    "Display",
    "VideoOutputWriter",
    "Activity",
    "ActivityClassifier",
    "ZoomController",
    "TrackingStrategy",
    "TrackingResult",
    "LargestPersonStrategy",
]

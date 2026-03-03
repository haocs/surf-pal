"""
main.py
-------
Surf-Pal: virtual cameraman for surf video.

Entry point — wires together the pipeline components and runs the main
frame-processing loop.  All non-trivial logic lives in the ``core`` package;
this file is intentionally kept as thin orchestration only.

Pipeline overview
-----------------
  VideoLoader ──► Detector ──► Tracker ──► ActivityClassifier
                                  │               │
                                  │         ZoomController
                                  │               │
                                  ▼               ▼
                            EventLogger      Cameraman
                                              │
                                    Display + VideoOutputWriter
"""

import cv2
import argparse
import time
from pathlib import Path

from core.video_loader import VideoLoader
from core.detector import Detector
from core.cameraman import Cameraman
from core.tracker import Tracker
from core.event_logger import EventLogger
from core.display import Display
from core.writer import VideoOutputWriter
from core.activity import ActivityClassifier
from core.zoom_controller import ZoomController


# ---------------------------------------------------------------------------
# Pipeline constants
# ---------------------------------------------------------------------------

OUTPUT_PATH = "tmp/output.mp4"
DEBUG_OUTPUT_PATH = "tmp/output_debug.mp4"
DEBUG_LOG_PATH = "tmp/debug_log.json"
ASSUMED_FPS = 30.0  # Fall back when the source doesn't report its own FPS
MODEL_PATH = Path(__file__).resolve().parent / "models" / "yolov8n.pt"


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def main(
    source,
    zoom_level: float = 2.0,
    show_debug: bool = True,
    debug_tracking: bool = False,
) -> None:
    """
    Run the surf-pal virtual camera pipeline on *source*.

    Args:
        source:          Video file path or webcam index (int).
        zoom_level:      Initial crop zoom factor forwarded to :class:`Cameraman`.
                         This sets the baseline output size; dynamic zoom varies
                         around it at runtime.
        show_debug:      Show the annotated World View and Virtual Camera windows.
        debug_tracking:  Draw target overlays, write a full-res debug video, and
                         save a JSON event log to ``tmp/debug_log.json``.
    """
    # ------------------------------------------------------------------
    # Initialise video source
    # ------------------------------------------------------------------
    loader = VideoLoader(source).start()

    # Block until the first frame is available so we know the frame dimensions
    while not loader.more():
        time.sleep(0.01)

    frame = loader.read()
    if frame is None:
        print("Could not read from video source.")
        return

    h, w = frame.shape[:2]
    # Use the source FPS if available; fall back to the assumed constant
    fps = loader.fps if loader.fps > 0 else ASSUMED_FPS

    # ------------------------------------------------------------------
    # Initialise pipeline components
    # ------------------------------------------------------------------
    detector = Detector(str(MODEL_PATH))
    cameraman = Cameraman(w, h, zoom_level=zoom_level)
    tracker = Tracker()  # uses LargestPersonStrategy by default
    event_logger = EventLogger(fps=fps)
    activity_classifier = ActivityClassifier()
    zoom_controller = ZoomController()
    display = Display(frame_height=h, debug_tracking=debug_tracking)

    writer = VideoOutputWriter(
        path=OUTPUT_PATH,
        fps=fps,
        crop_size=(cameraman.crop_w, cameraman.crop_h),
        debug_path=DEBUG_OUTPUT_PATH if debug_tracking else None,
        frame_size=(w, h),
    )

    print(f"Starting tracking on source: {source}")
    print("Press 'q' to quit.")

    # ------------------------------------------------------------------
    # Main frame loop
    # ------------------------------------------------------------------
    frame_count = 0

    while True:
        frame = loader.read()

        if frame is None:
            if loader.stopped:
                break           # Source exhausted
            time.sleep(0.01)   # Buffer momentarily empty — wait briefly
            continue

        frame_count += 1

        # --- Detect & Track ---
        results = detector.track(frame)

        # --- Select target (pluggable strategy) ---
        tracking_result = tracker.update(results)
        target_box = tracking_result.target_box
        locked_track_id = tracking_result.track_id

        # --- Classify activity + update dynamic zoom ---
        activity = activity_classifier.update(target_box, h)
        zoom = zoom_controller.update(activity)
        cameraman.set_zoom(zoom)

        # --- Log TRACKING / LOST state transitions ---
        event_logger.update(
            frame_count=frame_count,
            locked_track_id=locked_track_id,
            is_visible=(target_box is not None),
            prev_locked_id=tracking_result.prev_id,
        )

        # --- Compute virtual camera crop ---
        crop_rect = cameraman.update(target_box)
        cropped_view = cameraman.crop(frame, crop_rect)

        # --- Render & display debug view ---
        if show_debug:
            debug_frame = display.render(
                frame, results, crop_rect, target_box, locked_track_id,
                activity=activity, zoom_level=zoom,
                signals=activity_classifier.signals,
            )
            display.show(debug_frame, cropped_view)

            # Write full-res debug frame to file if the debug writer is active
            writer.write(cropped_view, debug_frame if writer.has_debug else None)
        else:
            writer.write(cropped_view)

        # Exit on 'q' keypress
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------
    loader.stop()
    writer.release()
    cv2.destroyAllWindows()

    if debug_tracking:
        event_logger.save(DEBUG_LOG_PATH)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Surf-Pal virtual cameraman")
    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help="Video source: '0' for webcam, or a path to a video file.",
    )
    parser.add_argument(
        "--zoom",
        type=float,
        default=2.0,
        help="Initial zoom level — e.g. 2.0 gives a 2× crop. Dynamic zoom varies around this.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help=(
            "Enable debug mode: draw target overlays, save a full-res debug "
            "video, and write a TRACKING/LOST event log."
        ),
    )
    args = parser.parse_args()

    # cv2.VideoCapture expects an int for webcam sources
    source = int(args.source) if args.source.isdigit() else args.source

    main(source, zoom_level=args.zoom, debug_tracking=args.debug)

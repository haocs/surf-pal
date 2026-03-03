"""
core/detector.py
----------------
YOLOv8-based person detector and tracker for surf-pal.

Wraps Ultralytics' YOLO model with ByteTrack multi-object tracking so every
detected person is assigned a persistent integer track ID across frames.
Device selection (CUDA → MPS → CPU) is automatic.
"""

from ultralytics import YOLO
import torch


class Detector:
    """
    Person detector / tracker using YOLOv8 + ByteTrack.

    Args:
        model_path: Path to the ``.pt`` weights file.
                    Defaults to ``'models/yolov8n.pt'`` (nano variant).
    """

    def __init__(self, model_path: str = "models/yolov8n.pt") -> None:
        # Prefer GPU (CUDA), then Apple Silicon (MPS), then fall back to CPU
        if torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"

        print(f"Using device: {self.device}")
        self.model = YOLO(model_path)

    def track(self, frame, classes: list = None, persist: bool = True):
        """
        Run detection + tracking on a single BGR frame.

        Args:
            frame:   BGR image array (H × W × 3) from ``cv2.VideoCapture``.
            classes: COCO class IDs to detect.  Defaults to
                     ``[0, 38]`` = person + surfboard.
            persist: Keep track IDs alive across frames (ByteTrack state).
                     Should remain ``True`` for smooth tracking.

        Returns:
            A single ``ultralytics.engine.results.Results`` object (the first
            element of the list returned by ``model.track``).
        """
        if classes is None:
            classes = [0, 38]  # 0 = person, 38 = surfboard (COCO)

        results = self.model.track(
            frame,
            classes=classes,
            persist=persist,
            verbose=False,          # suppress per-frame console noise
            device=self.device,
            tracker="bytetrack.yaml",
        )
        # model.track always returns a list; we only process one frame at a time
        return results[0]

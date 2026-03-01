# Recent History & Context for Agents

When resuming work, please review this document to understand the current state of the codebase.

## Recent Work Completed
1. **Python Activity Classifier Reform (`core/activity.py`)**:
   - The original classifier relied solely on horizontal speed, failing when a surfer compressed or dropped vertically.
   - We rewrote it to use **2D total displacement**, **vertical speed** (for wave drops), and **bounding box area variance** (for stance compression).
   - We added a "stickiness" timer (holding RIDING for ~15 frames) to prevent flicker.
   - We exposed real-time raw signal metrics (SPD, VSPD, VAR, AR) in the debug HUD (`display.py`, `main.py`).

2. **Native iOS App Development (`ios_app/`)**:
   - Built a Swift/SwiftUI app from scratch for on-device tracking.
   - Exported YOLOv8 PyTorch weights to CoreML format (`yolov8n.mlpackage`) using `ultralytics` (`models/export_coreml.py`).
   - Implemented `CameraManager.swift` using AVFoundation for video feed and video saving to the Photos library.
   - Implemented `Detector.swift` using Apple's Vision framework to run YOLOv8 ML predictions.
   - Implemented `Tracker.swift` leveraging `VNTrackObjectRequest` for fast, robust selected-object tracking.
   - Implemented `VirtualCameraman.swift` with Mathematical EMA smoothing to provide cinematic digital panning and zooming based on the tracker's bounding box.

## Repository Layout
- `core/`: Python tracking pipeline business logic.
- `main.py`: Entry point for Python tracking CLI.
- `ios_app/`: Swift source code and README for Xcode assembly.
- `models/`: ML export scripts. *Note: model weight binaries (`*.pt`, `*.mlpackage/`) are ignored via `.gitignore`.*

## Next Steps / Future Work
- The iOS app tracker currently tracks the box. It does not yet implement the advanced SURFING vs PADDLING activity heuristics that the Python `ActivityClassifier` uses.
- The iOS app UI could be refined further.

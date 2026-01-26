# Surfing Virtual PTZ System Implementation Plan

## Goal Description
Develop a "Virtual Cameraman" system that takes a wide-angle, high-resolution video feed (e.g., 4K) of a surf break and automatically generates a zoomed-in, stabilized video feed tracking a specific surfer. This allows for automated "close-up" capture from a fixed shore or pier camera.

## User Review Required
> [!IMPORTANT]
> **Performance vs. Quality**: Real-time processing of 4K video is computationally intensive. The system will prioritize frame rate for tracking but may need to skip frames for checking detection if hardware is limited.
> **Tracking Logic**: The system needs a way to select *which* surfer to track if multiple are present. The initial version will default to the largest detected person or the one closest to the center, or allow mouse-click selection in the preview window.

## Proposed Changes

### Project Structure
```
surfing-virtual-ptz/
├── main.py              # Application entry point (CLI & GUI loop)
├── core/
│   ├── video_loader.py  # High-performance video reading (Threaded)
│   ├── detector.py      # YOLOv8 wrapper
│   ├── tracker.py       # Object tracking logic (ByteTrack)
│   └── cameraman.py     # Virtual PTZ logic (smoothing, cropping)
├── utils/
│   └── display.py       # resizing/showing frames
├── requirements.txt
└── README.md
```

### Core Components

#### [MODIFY] [requirements.txt](file:///Users/hao/.gemini/antigravity/playground/dynamic-kilonova/requirements.txt)
- `ultralytics` (YOLOv8)
- `opencv-python`
- `numpy`
- `filterpy` (For Kalman filters if needed for smoothing, or just simple moving average first)

#### [NEW] [core/cameraman.py](file:///Users/hao/.gemini/antigravity/playground/dynamic-kilonova/core/cameraman.py)
This is the heart of the "auto zoom" feature.
- **Input**: Current frame, tracked object bbox (x, y, w, h).
- **State**: Current crop window (smooth_x, smooth_y, smooth_zoom).
- **Logic**:
    - Calculate desired crop center based on target center.
    - Apply exponential smoothing (moving average) or Kalman Filtering to transition from current crop to desired crop.
    - Prevent "jitter" by ignoring small movements.
    - Ensure crop stays within video boundaries.
- **Output**: Cropped image frame.

#### [NEW] [main.py](file:///Users/hao/.gemini/antigravity/playground/dynamic-kilonova/main.py)
- Initialize Video Stream (Webcam or File).
- Run YOLOv8 detection every N frames (for performance) or every frame (if GPU allows).
- Update Tracker.
- Pass target to `Cameraman` to get the cropped frame.
- Display "Live View" (Cropped) and "World View" (Full wide shot with boxes).
- Save the **Cropped** video to disk.

#### [NEW] [core/detector.py](file:///Users/hao/.gemini/antigravity/playground/dynamic-kilonova/core/detector.py)
- Load `yolov8n.pt` (nano) or `yolov8s.pt` (small) for balance of speed/acc.
- Filter for class `0` (person) and `38` (surfboard) if useful.

## Verification Plan

### Automated Tests
- Test `cameraman.py` logic with dummy coordinates to verify smoothing math (e.g., input jumps 100px, output moves gradually).
- Verification script to run on a sample 4K clip and output a 1080p cropped tracked video.

### Manual Verification
- Run on a sample surf video. Verified criteria:
    - [ ] Surfer stays in frame.
    - [ ] Camera movement is not jerky.
    - [ ] Resolution of cropped output is acceptable.

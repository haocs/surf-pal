# surf-pal
Your virtual camera man for surfing #vibe-coding

## Project Structure
This repository contains two parallel implementations of the Surf-Pal tracking system. Both use the YOLOv8 object detection model to locate surfers.

### 1. Python Pipeline (`core/` & `main.py`)
A computer-vision pipeline built with Python, OpenCV, and PyTorch. It processes pre-recorded video files or webcam streams, detects surfers, classifies their activity (riding, paddling, sitting) using motion heuristics, and applies a smoothed "virtual camera" crop.

**To run:**
```bash
python3 main.py --source samples/input.mp4 --debug
```

### 2. iOS Native App (`ios_app/`)
A completely native on-device iPhone application written in Swift and SwiftUI. It uses the exact same YOLOv8 model (converted to Apple's CoreML format for the Neural Engine) and Apple's Vision framework to continuously track a selected surfer in real-time through the live camera feed. It includes digital pan/zoom smoothing and video recording.

**To build:**
See [ios_app/README.md](ios_app/README.md) for instructions on how to assemble the Xcode project.

### 3. Models (`models/`)
Contains `yolov8n.pt`, `yolov8n.mlpackage`, and the script `export_coreml.py` to export PyTorch weights to CoreML for the iOS app.

# Surfing Virtual PTZ Usage Guide

This system uses YOLOv8 to detect surfers and a virtual cameraman algorithm to automatically pan, tilt, and zoom to keep them in frame.

## Quick Start

1.  **Activate Virtual Environment**:
    ```bash
    source venv/bin/activate
    ```

2.  **Run with a Video File**:
    ```bash
    python main.py --source /path/to/your/video.mp4 --zoom 2.0
    ```

3.  **Run with Webcam**:
    ```bash
    python main.py --source 0
    ```

## Controls

-   **q**: Quit the application.

## Troubleshooting

-   **"Could not read video source"**: Check if the file path is correct or if another application is using the webcam.
-   **No detections**: Ensure the model `yolov8n.pt` downloaded correctly (it should download automatically on first run).
-   **Jittery Movement**: Adjust the `smoothing_factor` in `core/cameraman.py` (currently 0.1). Lower values = smoother but slower reaction.

## Files
-   `main.py`: Entry point.
-   `core/cameraman.py`: Logic for smoothing and cropping.
-   `core/detector.py`: YOLOv8 wrapper.
-   `core/video_loader.py`: Efficient video reading.

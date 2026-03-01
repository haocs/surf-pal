"""
models/export_coreml.py
-----------------------
Utility script to convert YOLOv8 PyTorch weights into Apple's CoreML format
for use in the native iOS app.

Usage:
    cd models/
    python3 export_coreml.py
"""
from ultralytics import YOLO

def main():
    print("Loading YOLOv8n model...")
    # Load the YOLOv8n model (will download if not present)
    model = YOLO('yolov8n.pt')
    
    print("Exporting to CoreML format...")
    # Export the model to CoreML format
    # nms=True bakes Non-Maximum Suppression into the CoreML model so we don't have to write it in Swift
    model.export(format='coreml', nms=True)
    print("Done! The 'yolov8n.mlpackage' is ready to be added to your Xcode project.")

if __name__ == "__main__":
    main()

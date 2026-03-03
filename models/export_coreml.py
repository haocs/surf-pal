"""
models/export_coreml.py
-----------------------
Utility script to convert YOLOv8 PyTorch weights into Apple's CoreML format
for use in the native iOS app.

Usage:
    cd models/
    python3 export_coreml.py
"""
from pathlib import Path
import os
from ultralytics import YOLO

def main():
    models_dir = Path(__file__).resolve().parent
    pt_path = models_dir / "yolov8n.pt"
    output_path = models_dir / "yolov8n.mlpackage"

    if not pt_path.exists():
        print(f"Missing weights at {pt_path}")
        print("Place yolov8n.pt in models/ before exporting.")
        return

    # Export output is created in the current working directory.
    os.chdir(models_dir)

    print("Loading YOLOv8n model...")
    model = YOLO(str(pt_path))
    
    print("Exporting to CoreML format...")
    # Export the model to CoreML format
    # nms=True bakes Non-Maximum Suppression into the CoreML model so we don't have to write it in Swift
    model.export(format='coreml', nms=True)
    print(f"Done! CoreML model exported to {output_path}")

if __name__ == "__main__":
    main()

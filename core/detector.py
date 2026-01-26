from ultralytics import YOLO
import torch

class Detector:
    def __init__(self, model_path='yolov8n.pt'):
        self.device = 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
        print(f"Using device: {self.device}")
        self.model = YOLO(model_path)
    
    def track(self, frame, classes=[0, 38], persist=True):
        # Run tracking
        results = self.model.track(frame, classes=classes, persist=persist, verbose=False, device=self.device, tracker="bytetrack.yaml")
        return results[0]

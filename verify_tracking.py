
import cv2
import numpy as np
import time
from core.detector import Detector
from core.cameraman import Cameraman

def create_synthetic_video(filename, width=3840, height=2160, frames=100):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, 30.0, (width, height))
    
    # Create a moving white square
    square_size = 200
    x, y = 1000, 1000
    dx, dy = 10, 5 # Movement speed
    
    print(f"Generating synthetic video: {filename}...")
    for i in range(frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Draw "surfer" (just a white box for now)
        # Note: YOLO might not detect a white box as a person.
        # So we might need to rely on the fact that I can't easily fake a person for YOLO 
        # without downloading an image. 
        # ALTERNATIVELY: We can mock the detector to return a box around our white square
        # so we can test the Cameraman logic specifically.
        
        cv2.rectangle(frame, (x, y), (x + square_size, y + square_size), (255, 255, 255), -1)
        out.write(frame)
        
        x += dx
        y += dy
        
        # Bounce off walls
        if x <= 0 or x + square_size >= width: dx = -dx
        if y <= 0 or y + square_size >= height: dy = -dy
        
    out.release()
    print("Video generated.")

class MockDetector:
    def track(self, frame):
        # Find the white square
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        class MockResult:
            def __init__(self, box):
                self.boxes = box
            def plot(self):
                return frame
                
        if contours:
            c = contours[0]
            x, y, w, h = cv2.boundingRect(c)
            # Create a mock box object that looks like YOLO's
            # box.xyxy[0], box.cls[0]
            
            class MockBox:
                def __init__(self, x, y, w, h):
                    self.xyxy = np.array([[x, y, x+w, y+h]])
                    self.cls = [0] # Person class
                    
            return MockResult([MockBox(x, y, w, h)])
        
        return MockResult(None)

def run_verification():
    video_path = "synthetic_surf.mp4"
    create_synthetic_video(video_path, frames=60)
    
    # Initialize
    # We use MockDetector because YOLO won't detect a white square as a person
    detector = MockDetector() 
    
    cap = cv2.VideoCapture(video_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    cameraman = Cameraman(w, h, zoom_level=2.0)
    
    output_path = "verified_output.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 30.0, (cameraman.crop_w, cameraman.crop_h))
    
    print("Running tracking verification...")
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        results = detector.track(frame)
        
        target_box = None
        if results.boxes:
            for box in results.boxes:
                target_box = box.xyxy[0]
                break
                
        crop_rect = cameraman.update(target_box)
        cropped_view = cameraman.crop(frame, crop_rect)
        
        out.write(cropped_view)
        frame_count += 1
        
    cap.release()
    out.release()
    print(f"Verification complete. Processed {frame_count} frames.")
    print(f"Output saved to {output_path}")

if __name__ == "__main__":
    run_verification()

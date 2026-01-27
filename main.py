import cv2
import argparse
import time
from core.video_loader import VideoLoader
from core.detector import Detector
from core.cameraman import Cameraman

def main(source, zoom_level=2.0, show_debug=True, debug_tracking=False):
    # Initialize components
    loader = VideoLoader(source).start()
    detector = Detector('yolov8n.pt') 
    
    # Wait for first frame to get dimensions
    while not loader.more():
        time.sleep(0.1)
    
    # Get dimensions
    frame = loader.read()
    if frame is None:
        print("Could not read video source")
        return
        
    h, w = frame.shape[:2]
    cameraman = Cameraman(w, h, zoom_level=zoom_level)
    
    # Output writer (optional, to save the cropped video)
    # We will save to 'output.mp4'
    crop_w = cameraman.crop_w
    crop_h = cameraman.crop_h
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('output.mp4', fourcc, 30.0, (crop_w, crop_h))

    # Debug output writer
    debug_out = None
    if debug_tracking:
        debug_out = cv2.VideoWriter('output_debug.mp4', fourcc, 30.0, (w, h))

    print(f"Starting tracking on source: {source}")
    print("Press 'q' to quit.")
    
    while True:
        frame = loader.read()
        if frame is None:
            if loader.stopped:
                break
            time.sleep(0.01)
            continue
            
        # Detect & Track
        # Using persist=True for tracking
        results = detector.track(frame)
        
        target_box = None
        
        # Logic to select primary target
        # For now: select the person with the largest bounding box area
        max_area = 0
        
        if results.boxes is not None:
            for box in results.boxes:
                # box.xyxy is [x1, y1, x2, y2]
                coords = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = coords
                area = (x2 - x1) * (y2 - y1)
                
                # Check if it's a person (class 0)
                cls = int(box.cls[0])
                if cls == 0: 
                    if area > max_area:
                        max_area = area
                        target_box = coords

        # Update Cameraman
        crop_rect = cameraman.update(target_box)
        x, y, crop_w, crop_h = crop_rect
        
        # Get processed frame
        cropped_view = cameraman.crop(frame, crop_rect)
        
        if show_debug:
            # Draw tracking info on original frame
            debug_frame = frame.copy()
            if results.boxes is not None:
                # Plot all results
                res_plotted = results.plot()
                debug_frame = res_plotted
            
            # Draw the crop window on the main frame
            cv2.rectangle(debug_frame, (x, y), (x + crop_w, y + crop_h), (0, 255, 255), 4)

            # Draw tracked object outline if debug_tracking is enabled
            if debug_tracking and target_box is not None:
                tx1, ty1, tx2, ty2 = map(int, target_box)
                cv2.rectangle(debug_frame, (tx1, ty1), (tx2, ty2), (0, 255, 0), 2)
            
            # Write full resolution debug frame to file if tracking is enabled
            if debug_out is not None:
                debug_out.write(debug_frame)
            
            # Resize debug frame to fit screen if 4K
            display_h, display_w = debug_frame.shape[:2]
            if display_w > 1920:
                scale = 1920 / display_w
                debug_frame = cv2.resize(debug_frame, (int(display_w*scale), int(display_h*scale)))

            cv2.imshow("World View", debug_frame)
            cv2.imshow("Virtual Camera", cropped_view)

        # Write to output
        out.write(cropped_view)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    loader.stop()
    out.release()
    if debug_out is not None:
        debug_out.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=str, default='0', help='Video source (0 for webcam, or path to file)')
    parser.add_argument('--zoom', type=float, default=2.0, help='Zoom level (e.g. 2.0 for 2x zoom)')
    parser.add_argument('--debug', action='store_true', help='Draw outline around tracked object')
    args = parser.parse_args()
    
    # Handle numeric source for webcam
    source = args.source
    if source.isdigit():
        source = int(source)
        
    main(source, args.zoom, debug_tracking=args.debug)

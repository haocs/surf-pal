import cv2
import argparse
import time
from core.video_loader import VideoLoader
from core.detector import Detector
from core.cameraman import Cameraman

import json
import datetime

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
    # We will save to 'tmp/output.mp4'
    crop_w = cameraman.crop_w
    crop_h = cameraman.crop_h
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('tmp/output.mp4', fourcc, 30.0, (crop_w, crop_h))

    # Debug output writer
    debug_out = None
    if debug_tracking:
        debug_out = cv2.VideoWriter('tmp/output_debug.mp4', fourcc, 30.0, (w, h))

    print(f"Starting tracking on source: {source}")
    print("Press 'q' to quit.")
    
    locked_track_id = None
    prev_visible = False
    
    # Logging
    debug_log = []
    video_start_time = time.time() # This is wall clock, but for video timestamp we might just use frame count / fps
    frame_count = 0
    fps = 30.0 # Assumption, or get from loader if possible
    
    while True:
        frame = loader.read()
        if frame is None:
            if loader.stopped:
                break
            time.sleep(0.01)
            continue
            
        frame_count += 1
        video_timestamp = (frame_count / fps) * 1000 # Milliseconds
        
        # Detect & Track
        # Using persist=True for tracking
        results = detector.track(frame)
        
        target_box = None
        current_track_id = None
        
        # Parse all detections into a dictionary: track_id -> box
        # and also find the largest person if we need to fall back
        detections = {}
        max_area = 0
        largest_person_id = None
        largest_person_box = None
        
        if results.boxes is not None:
            for box in results.boxes:
                # box.xyxy is [x1, y1, x2, y2]
                coords = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = coords
                area = (x2 - x1) * (y2 - y1)
                
                # Get track ID if available
                track_id = int(box.id[0]) if box.id is not None else None
                
                # Check if it's a person (class 0)
                cls = int(box.cls[0])
                if cls == 0: 
                    if track_id is not None:
                        detections[track_id] = coords
                        
                    if area > max_area:
                        max_area = area
                        largest_person_box = coords
                        largest_person_id = track_id

        # Logic to select target
        prev_locked_id = locked_track_id
        
        # 1. Try to find the locked target
        if locked_track_id is not None and locked_track_id in detections:
            target_box = detections[locked_track_id]
            current_track_id = locked_track_id
        else:
            # 2. If locked target not found (or no lock yet), pick the largest person
            if largest_person_box is not None:
                target_box = largest_person_box
                current_track_id = largest_person_id
                locked_track_id = current_track_id # Update lock
            else:
                # No person found at all
                pass
        
        # Log state changes
        # Determine visibility
        curr_visible = (target_box is not None)
        
        # Check for ID change
        if prev_locked_id != locked_track_id:
            if locked_track_id is not None:
                # New lock acquired (or switched)
                debug_log.append({
                    "timestamp": video_timestamp,
                    "event": "TRACKING",
                    "track_id": locked_track_id
                })
        
        # Check for visibility change (only if ID is same and valid)
        elif locked_track_id is not None:
            # Re-acquired visibility
            if curr_visible and not prev_visible:
                 debug_log.append({
                    "timestamp": video_timestamp,
                    "event": "TRACKING",
                    "track_id": locked_track_id
                })
            # Lost visibility
            elif not curr_visible and prev_visible:
                 debug_log.append({
                    "timestamp": video_timestamp,
                    "event": "LOST",
                    "track_id": locked_track_id
                })

        # Update previous state
        prev_visible = curr_visible


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
            if debug_tracking:
                # Bottom-left UI coordinates
                ui_x = 30
                ui_y = h - 30
                
                if target_box is not None:
                    tx1, ty1, tx2, ty2 = map(int, target_box)
                    cv2.rectangle(debug_frame, (tx1, ty1), (tx2, ty2), (0, 255, 0), 2)
                    
                    # UI Info
                    text = f"TRACKING ID: {locked_track_id}"
                    cv2.putText(debug_frame, text, (ui_x, ui_y), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                elif locked_track_id is not None:
                    # Message if locked target is lost
                    text = f"LOST ID: {locked_track_id}"
                    cv2.putText(debug_frame, text, (ui_x, ui_y), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            
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
    
    # Save log
    if debug_tracking:
        with open('tmp/debug_log.json', 'w') as f:
            json.dump(debug_log, f, indent=2)
        print("Debug log saved to tmp/debug_log.json")

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

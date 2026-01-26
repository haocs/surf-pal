import cv2
import numpy as np

class Cameraman:
    def __init__(self, source_width, source_height, zoom_level=2.0, smoothing_factor=0.1):
        self.src_w = source_width
        self.src_h = source_height
        self.zoom = zoom_level
        self.alpha = smoothing_factor
        
        # Target crop size
        self.crop_w = int(self.src_w / self.zoom)
        self.crop_h = int(self.src_h / self.zoom)
        
        # Current center (start at center of frame)
        self.current_center_x = self.src_w // 2
        self.current_center_y = self.src_h // 2

    def update(self, target_bbox):
        """
        Update the camera position based on target bounding box (x1, y1, x2, y2).
        If target_bbox is None, drift back to center or stay put.
        """
        if target_bbox is not None:
            x1, y1, x2, y2 = target_bbox
            target_cx = (x1 + x2) / 2
            target_cy = (y1 + y2) / 2
        else:
            # If lost tracking, maybe just stay put or slowly center
            target_cx = self.current_center_x 
            target_cy = self.current_center_y

        # Smooth transition
        self.current_center_x = (1 - self.alpha) * self.current_center_x + self.alpha * target_cx
        self.current_center_y = (1 - self.alpha) * self.current_center_y + self.alpha * target_cy

        # Ensure crop is within bounds
        # Top-left corner of the crop
        x_start = int(self.current_center_x - self.crop_w / 2)
        y_start = int(self.current_center_y - self.crop_h / 2)

        # Clamping
        x_start = max(0, min(x_start, self.src_w - self.crop_w))
        y_start = max(0, min(y_start, self.src_h - self.crop_h))
        
        return x_start, y_start, self.crop_w, self.crop_h

    def crop(self, frame, crop_rect):
        x, y, w, h = crop_rect
        return frame[y:y+h, x:x+w]

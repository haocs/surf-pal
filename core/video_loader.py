import cv2
import threading
import time
from queue import Queue

class VideoLoader:
    def __init__(self, source, queue_size=128):
        self.source = source
        self.cap = cv2.VideoCapture(source)
        self.q = Queue(maxsize=queue_size)
        self.stopped = False
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
    def start(self):
        t = threading.Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        return self

    def update(self):
        while True:
            if self.stopped:
                return
            
            if not self.q.full():
                ret, frame = self.cap.read()
                if not ret:
                    self.stop()
                    return
                self.q.put(frame)
            else:
                time.sleep(0.01)

    def read(self):
        return self.q.get() if not self.q.empty() else None

    def more(self):
        return not self.q.empty()

    def stop(self):
        self.stopped = True
        if self.cap.isOpened():
            self.cap.release()

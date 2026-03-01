"""
core/video_loader.py
--------------------
Threaded video frame reader for surf-pal.

Reading frames in the main thread on high-resolution video (e.g. 4K) can
cause the processing pipeline to drop frames while waiting on disk I/O.
VideoLoader decouples I/O from processing by reading frames on a background
thread and buffering them in a Queue so the main loop always has a frame
ready to consume.
"""

import cv2
import threading
import time
from queue import Queue


class VideoLoader:
    """
    Asynchronous video reader backed by a bounded FIFO queue.

    The background thread continuously reads frames from the video source
    and pushes them into ``self.q``.  The main thread calls ``read()`` to pop
    frames without blocking on disk I/O.

    Args:
        source:     ``cv2.VideoCapture``-compatible source — an integer for a
                    webcam index or a file path string.
        queue_size: Maximum number of frames to buffer.  Larger values smooth
                    out I/O hiccups at the cost of extra memory.
    """

    def __init__(self, source, queue_size: int = 128) -> None:
        self.source = source
        self.cap = cv2.VideoCapture(source)
        self.q: Queue = Queue(maxsize=queue_size)
        self.stopped: bool = False

        # Cache video metadata so callers do not need to touch cap directly
        self.total_frames: int = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps: float = self.cap.get(cv2.CAP_PROP_FPS)
        self.width: int = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height: int = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def start(self) -> "VideoLoader":
        """Spawn the background reader thread and return ``self`` for chaining."""
        t = threading.Thread(target=self.update, args=(), daemon=True)
        t.start()
        return self

    def update(self) -> None:
        """
        Background thread entry point.

        Continuously reads frames from ``self.cap`` and puts them into the
        queue.  Stops when ``self.stopped`` is set or the source is exhausted.
        Sleeps briefly when the queue is full to avoid busy-waiting.
        """
        while True:
            if self.stopped:
                return

            if not self.q.full():
                ret, frame = self.cap.read()
                if not ret:
                    # Source exhausted (end of file or camera disconnected)
                    self.stop()
                    return
                self.q.put(frame)
            else:
                # Queue full — yield the CPU briefly rather than spinning
                time.sleep(0.01)

    def read(self):
        """
        Pop and return the next buffered frame, or ``None`` if the queue is
        empty (i.e. the reader has not yet warmed up or the source is done).
        """
        return self.q.get() if not self.q.empty() else None

    def more(self) -> bool:
        """Return ``True`` when at least one frame is ready to be consumed."""
        return not self.q.empty()

    def stop(self) -> None:
        """Signal the background thread to exit and release the capture device."""
        self.stopped = True
        if self.cap.isOpened():
            self.cap.release()

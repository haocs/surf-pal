import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    print("Importing core modules...")
    from core.video_loader import VideoLoader
    from core.detector import Detector
    from core.cameraman import Cameraman
    import main
    print("All modules imported successfully.")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

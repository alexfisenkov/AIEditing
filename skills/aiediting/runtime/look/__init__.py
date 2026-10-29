"""Looking at a source: snapshots, layout guess, secret-looking text, following a moving area."""
from .errors import LookError
from .frames import frame_time, frames
from .layout import detect_layout
from .ocr import ocr_backend
from .secrets import find_secrets
from .track import track_region

__all__ = ["LookError", "detect_layout", "find_secrets", "frame_time", "frames", "ocr_backend",
           "track_region"]

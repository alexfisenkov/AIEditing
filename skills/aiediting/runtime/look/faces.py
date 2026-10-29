"""Face finder: YuNet through OpenCV. Both the package and the model come from `ae.py doctor`."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Dict, List

from .errors import DOCTOR, LookError, need

MODEL = "face_detection_yunet_2023mar.onnx"


def models_dir() -> Path:
    """~/.aiediting/models on macOS, %LOCALAPPDATA%\\AIEditing\\models on Windows."""
    if sys.platform.startswith("win") and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AIEditing" / "models"
    return Path.home() / ".aiediting" / "models"


def model_path() -> Path:
    """AIEDITING_YUNET_MODEL overrides the default place of the YuNet model."""
    return Path(os.environ.get("AIEDITING_YUNET_MODEL") or models_dir() / MODEL)


def yunet(threshold: float = 0.7) -> Callable[[Path], List[Dict]]:
    """A detector: image path -> [{"x","y","w","h","score"}] in pixels, best first."""
    cv2 = need("cv2", "поиск лица (YuNet)")
    np = need("numpy", "поиск лица (YuNet)")
    model = model_path()
    if not model.is_file():
        raise LookError("Нет модели лица YuNet ({}): {}.".format(model, DOCTOR))

    def detect(path) -> List[Dict]:
        data = np.fromfile(str(path), dtype=np.uint8)  # imread cannot open non-ASCII paths on Windows
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            raise LookError("Не удалось прочитать кадр {}".format(path))
        h, w = img.shape[:2]
        det = cv2.FaceDetectorYN.create(str(model), "", (w, h), threshold)
        _, found = det.detect(img)
        faces = [{"x": int(f[0]), "y": int(f[1]), "w": int(f[2]), "h": int(f[3]),
                  "score": float(f[-1])} for f in (found if found is not None else [])]
        return sorted(faces, key=lambda f: -f["score"])

    return detect

"""The face track, one point per 0.5 s: [t, cx, cy, h] as shares of the frame, smoothed (src/data/face.json).

YuNet through OpenCV. Without the model, without OpenCV or without a face the frame holds the centre and
the person is told so: the speaker's frame then does not follow the head.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional, Tuple

from .common import warn, write_atomic

CENTRE = [0.0, 0.5, 0.45, 0.4]
SMOOTH = 8  # points each side: +-4 s, so the frame glides instead of jerking after the head


def model_path() -> Path:
    env = os.environ.get("AIEDITING_YUNET_MODEL")
    if env:
        return Path(env).expanduser()
    root = Path(os.environ["LOCALAPPDATA"]) / "AIEditing" if os.name == "nt" and os.environ.get("LOCALAPPDATA") else Path.home() / ".aiediting"
    return root / "models" / "face_detection_yunet_2023mar.onnx"


def _raw_points(video: Path, model: Path) -> Tuple[List[list], int]:
    import cv2  # optional: only this step needs it

    cap = cv2.VideoCapture(str(video))
    width, height = int(cap.get(3)), int(cap.get(4))
    fps = cap.get(5) or 30.0
    count = int(cap.get(7))
    detector = cv2.FaceDetectorYN_create(str(model), "", (width, height), 0.6)
    step = max(1, int(round(fps / 2)))
    points, found = [], 0
    for k, index in enumerate(range(0, count, step)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = cap.read()
        if not ok:
            break
        _, faces = detector.detect(frame)
        if faces is None or len(faces) == 0:
            points.append([k * 0.5, None, None, None])
            continue
        f = max(faces, key=lambda x: x[2] * x[3])
        points.append([k * 0.5, float(f[0] + f[2] / 2) / width, float(f[1] + f[3] / 2) / height, float(f[3]) / height])
        found += 1
    cap.release()
    return points, found


def _fill(points: List[list]) -> bool:
    """Holes take the previous value; returns False if the face was never found."""
    last = next((p for p in points if p[1] is not None), None)
    if last is None:
        return False
    for p in points:
        if p[1] is None:
            p[1:] = last[1:]
        else:
            last = p
    return True


def _smooth(points: List[list]) -> List[list]:
    out = []
    for i, p in enumerate(points):
        window = points[max(0, i - SMOOTH): i + SMOOTH + 1]
        out.append([round(p[0], 2)] + [round(sum(q[k] for q in window) / len(window), 4) for k in (1, 2, 3)])
    return out


def build_track(video: Path, work: Path, again: bool = False) -> str:
    """Write src/data/face.json; returns a one-line summary for the report. `again`: the video has changed."""
    target = work / "src" / "data" / "face.json"
    if target.is_file() and not again:
        try:
            have = json.loads(target.read_text(encoding="utf-8"))
        except ValueError:
            have = [CENTRE]
        if have != [CENTRE]:  # a real track from an earlier run: a repeat does not replace it by a worse one
            return "трек лица уже построен ({} отсчётов); чтобы построить заново, удалите src/data/face.json".format(len(have))
    reason: Optional[str] = None
    model = model_path()
    try:
        import cv2  # noqa: F401
    except ImportError:
        reason = "нет OpenCV (cv2) в этом Python"
    if reason is None and not model.is_file():
        reason = "нет модели лица {} (путь можно задать в AIEDITING_YUNET_MODEL)".format(model)
    if reason is None:
        try:
            points, found = _raw_points(video, model)
        except Exception as exc:  # OpenCV raises its own error types
            points, found, reason = [], 0, "лицо не прочиталось ({})".format(str(exc).splitlines()[0][:80])
        if reason is None and (not points or not _fill(points)):
            reason = "лицо в кадре не найдено"
        if reason is None:
            write_atomic(target, json.dumps(_smooth(points)))
            return "лицо найдено в {} из {} отсчётов, трек сглажен".format(found, len(points))
    warn("{}: рамка спикера держит центр кадра и за головой не следует.".format(reason))
    write_atomic(target, json.dumps([CENTRE]))
    return "лицо не отслежено ({}), рамка по центру".format(reason)

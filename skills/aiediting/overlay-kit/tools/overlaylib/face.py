"""The face track, one point per 0.5 s: [t, cx, cy, h, since] as shares of the frame (src/data/face.json).

`since` is the second at which the point's piece of the picture began: a scene change or a hard cut. The track is smoothed
inside each piece and never through a cut (facecuts.py), so right after a cut the speaker's frame is already on the new face.

YuNet through OpenCV. Without the model, without OpenCV or without a face the frame holds the centre and
the person is told so: the speaker's frame then does not follow the head.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from . import facecuts, vmap
from .common import warn, write_atomic

CENTRE = [0.0, 0.5, 0.45, 0.4]
STEP = 0.5  # seconds between the points


def model_path() -> Path:
    env = os.environ.get("AIEDITING_YUNET_MODEL")
    if env:
        return Path(env).expanduser()
    root = Path(os.environ["LOCALAPPDATA"]) / "AIEditing" if os.name == "nt" and os.environ.get("LOCALAPPDATA") else Path.home() / ".aiediting"
    return root / "models" / "face_detection_yunet_2023mar.onnx"


def _read(video: Path, model: Path) -> Tuple[List[list], int, List[float]]:
    """(points with holes filled, how many had a face, for every point the second its piece began)."""
    import cv2  # optional: only this step needs it

    cap = cv2.VideoCapture(str(video))
    try:
        width, height = int(cap.get(3)), int(cap.get(4))
        fps = cap.get(5) or 30.0
        count = int(cap.get(7))
        detector = cv2.FaceDetectorYN_create(str(model), "", (width, height), 0.6)
        step = max(1, int(round(fps * STEP)))
        seen = {}

        def faces_at(index: int) -> Optional[List[facecuts.Face]]:
            """Every face of a frame; None when the frame cannot be read."""
            if index not in seen:
                cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, frame = cap.read()
                found = detector.detect(frame)[1] if ok else None
                seen[index] = None if not ok else [
                    (float(f[0] + f[2] / 2) / width, float(f[1] + f[3] / 2) / height, float(f[3]) / height)
                    for f in (found if found is not None else []) if f[3] > 0]
            return seen[index]

        points, found, last = [], 0, None
        for k, index in enumerate(range(0, count, step)):
            faces = faces_at(index)
            if faces is None:
                break
            face = facecuts.pick(faces, last)
            if face is None:
                points.append([k * STEP, None, None, None])
                continue
            points.append([k * STEP, face[0], face[1], face[2]])
            last = face
            found += 1
        if not points or not _fill(points):
            return points, 0, []
        facecuts.drop_blips(points)
        cuts = facecuts.find_cuts(points, step, lambda index, near: facecuts.pick(faces_at(index) or [], near))
        return points, found, facecuts.pieces(len(points), step, STEP / step, cuts)
    finally:
        cap.release()


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


def cuts_of(track: Sequence[Sequence[float]]) -> List[float]:
    """The seconds at which the pieces of a track begin (none for a track written before the pieces)."""
    return sorted({p[4] for p in track if len(p) > 4 and p[4] > 0})


def is_old_kind(track: Sequence[Sequence[float]]) -> bool:
    """Four numbers a point: written before the pieces, one smoothing through the whole video."""
    return track != [CENTRE] and any(len(p) < 5 for p in track)


def load(work: Path) -> List[list]:
    """src/data/face.json, or the centre when it is missing or unreadable."""
    try:
        have = json.loads((work / "src" / "data" / "face.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [CENTRE]
    return have if isinstance(have, list) and have else [CENTRE]


def detect(video: Path) -> Tuple[Optional[List[list]], str]:
    """(track, summary). Without OpenCV, the model or a face the track is None and the summary is the reason."""
    model = model_path()
    try:
        import cv2  # noqa: F401
    except ImportError:
        return None, "нет OpenCV (cv2) в этом Python"
    if not model.is_file():
        return None, "нет модели лица {} (путь можно задать в AIEDITING_YUNET_MODEL)".format(model)
    try:
        points, found, since = _read(video, model)
    except Exception as exc:  # OpenCV raises its own error types
        return None, "лицо не прочиталось ({})".format((str(exc).splitlines() or [type(exc).__name__])[0][:80])
    if not found:
        return None, "лицо в кадре не найдено"
    track = facecuts.smooth(points, since)
    cuts = cuts_of(track)
    where = " ({})".format(", ".join("{:g}".format(c) for c in cuts)) if cuts else ""
    return track, "лицо найдено в {} из {} отсчётов; смен кадра и склеек со скачком лица: {}{}; трек сглажен внутри кусков".format(
        found, len(points), len(cuts), where)


def _kept(have: list, marked: bool) -> str:
    """The line about a track that a repeat leaves in place. `marked`: the folder was edited by markers."""
    note = "трек лица уже построен ({} отсчётов); его склейки и пересборка: overlay.py face <папка>".format(len(have))
    if marked:  # the scenes read it in the seconds of the first accepted video: a rebuild from this file would break every frame
        note += ". В папке карта времени: трек живёт в секундах первого принятого ролика, не удаляйте его"
    if is_old_kind(have):
        note += ". Трек прежнего образца: сглажен сквозь смены кадра, после склейки рамка спикера может отставать от лица"
    return note


def build_track(video: Path, work: Path, again: bool = False) -> str:
    """Write src/data/face.json; returns a one-line summary for the report. `again`: the video has changed."""
    target = work / "src" / "data" / "face.json"
    marked = bool(vmap.load_rows(work))
    if target.is_file() and not again:
        have = load(work)
        if have != [CENTRE]:  # a real track from an earlier run: a repeat does not replace it by a worse one
            return _kept(have, marked)
    track, note = detect(video)
    if track is None:
        warn("{}: рамка спикера держит центр кадра и за головой не следует.".format(note))
        write_atomic(target, json.dumps([CENTRE]))
        return "лицо не отслежено ({}), рамка по центру".format(note)
    write_atomic(target, json.dumps(track))
    if marked:
        warn("в папке карта времени (правки по маркерам), а трек лица построен заново в секундах этого файла. Сцены читают его в секундах "
             "первого принятого ролика: рамка спикера разойдётся с лицом. Нужен трек того ролика: overlay.py face <папка> --rebuild --video <он>, "
             "или prepare с --keep-face при прежнем src/data/face.json.")
    return note

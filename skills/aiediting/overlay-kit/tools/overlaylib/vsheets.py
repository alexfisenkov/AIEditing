"""Contact sheets of vertical clips with the real second written on every frame (needs OpenCV and numpy).

The second on a cell comes from the frame number or from the time the frame was asked for, never from the position of the
file in a folder: files of a render come in a row, and a label counted from their order once misled the critics.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import List, Sequence, Tuple

from . import vspans
from .common import ToolError, ffmpeg

CELL = (300, 533)  # width, height of a cell of a frame sheet
COLS, ROWS = 6, 4
YELLOW = (0, 255, 255)  # BGR
GREEN = (120, 200, 90)
FRAME_FILE = re.compile(r"^f-(\d+)\.jpe?g$")
SHEET = re.compile(r"^sheet-\d+\.jpg$")


def _cv():
    try:
        import cv2
        import numpy
        return cv2, numpy
    except ImportError:
        raise ToolError("Для листов нужны OpenCV и numpy (они есть в окружении AIEditing: ~/.aiediting/venv).")


def frame_of(name: str) -> int:
    """The frame number a rendered file is named by (f-<frame>.jpeg)."""
    found = FRAME_FILE.match(name)
    if not found:
        raise ToolError("Файл кадра с неожиданным именем: {}".format(name))
    return int(found.group(1))


def pick(frames: Sequence[int], fps: float, every: float) -> List[Tuple[float, int]]:
    """[(second, frame)]: frames at least `every` seconds apart, each with its own second."""
    out: List[Tuple[float, int]] = []
    last = -1e9
    for frame in sorted(frames):
        t = vspans.frame_seconds(frame, fps)
        if t - last >= every - 1e-3:
            out.append((t, frame))
            last = t
    return out


def label(t: float) -> str:
    return "{:.1f} s".format(t)


def _read(path: Path, size: Tuple[int, int]):
    cv2, np = _cv()
    img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ToolError("Не читается кадр {}".format(path))
    return cv2.resize(img, size, interpolation=cv2.INTER_AREA)


def _stamp(img, t: float, zone=None):
    cv2, _ = _cv()
    if zone:
        k = img.shape[1] / 1080.0
        x0, y0, x1, y1 = zone
        cv2.rectangle(img, (int(x0 * k), int(y0 * k)), (int(x1 * k), int(y1 * k)), GREEN, 1)
    cv2.rectangle(img, (0, 0), (74, 20), YELLOW, -1)
    cv2.putText(img, label(t), (4, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    return img


def _grid(cells: List, cols: int, size: Tuple[int, int], out: Path) -> None:
    cv2, np = _cv()
    rows = (len(cells) + cols - 1) // cols
    canvas = np.full((rows * (size[1] + 4), cols * (size[0] + 4), 3), 70, dtype=np.uint8)
    for i, cell in enumerate(cells):
        y, x = (i // cols) * (size[1] + 4), (i % cols) * (size[0] + 4)
        canvas[y:y + size[1], x:x + size[0]] = cell
    ok, buf = cv2.imencode(".jpg", canvas, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not ok:
        raise ToolError("Лист не собрался: {}".format(out))
    tmp = out.with_name(out.stem + ".part" + out.suffix)
    tmp.write_bytes(buf.tobytes())
    tmp.replace(out)


def frame_sheets(frames_dir: Path, out_dir: Path, fps: float, every: float, zone) -> List[Path]:
    """Sheets of 24 frames: one frame per `every` seconds of the files in `frames_dir`, the safe zone drawn thin green."""
    files = {frame_of(p.name): p for p in frames_dir.iterdir() if FRAME_FILE.match(p.name)}
    if not files:
        raise ToolError("В {} нет кадров.".format(frames_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.iterdir():
        if SHEET.match(old.name):
            old.unlink()
    chosen = pick(list(files), fps, every)
    made = []
    for n in range(0, len(chosen), COLS * ROWS):
        cells = [_stamp(_read(files[frame], CELL), t, zone) for t, frame in chosen[n:n + COLS * ROWS]]
        target = out_dir / "sheet-{:02d}.jpg".format(n // (COLS * ROWS) + 1)
        _grid(cells, COLS, CELL, target)
        made.append(target)
    return made


def file_cell(video: Path, t: float, size: Tuple[int, int], work: Path):
    """One frame of a finished file at the second `t`, with that second on it."""
    shot = work / "{:.3f}.jpg".format(t)
    ffmpeg("-ss", "{:.3f}".format(t), "-i", video, "-frames:v", "1", "-q:v", "3", shot, what="Кадр на {:.1f} с".format(t))
    if not shot.is_file():
        raise ToolError("В файле {} нет кадра на {:.1f} с.".format(video.name, t))
    return _stamp(_read(shot, size), t)


def file_sheets(video: Path, out_dir: Path, total: float, step: float) -> List[Path]:
    """From the file itself: the whole clip every `step` seconds, and its tail every half second down to the last frame."""
    if step <= 0:
        raise ToolError("Шаг должен быть положительным числом секунд.")
    size, cols = (240, 426), 8
    last = max(0.0, total - 0.05)  # a frame exists only before the end
    whole = [min(k * step, last) for k in range(int(total // step) + 1)]
    tail = [max(0.0, total - 4.2 + k * 0.5) for k in range(8)] + [max(0.0, total - 0.1)]
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    with tempfile.TemporaryDirectory(prefix="vsheet-") as raw:
        for suffix, times in (("all", whole), ("tail", tail)):
            cells = [file_cell(video, t, size, Path(raw)) for t in times]
            target = out_dir / "{}-{}.jpg".format(video.stem, suffix)
            _grid(cells, cols, size, target)
            made.append(target)
    return made


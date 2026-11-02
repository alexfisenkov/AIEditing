"""Looking at a video: contact sheets, a sheet of the whole video, single frames of any video."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

from .common import ToolError, ffmpeg, say, write_atomic
from .media import duration_of, probe

SHEET = re.compile(r"^sheet-\d+\.jpg$")


def contact_sheets(video: Path, folder: Path, step: float, cols: int = 5, rows: int = 6) -> List[Path]:
    """30 frames per sheet, one every `step` seconds; old sheets of the same name pattern are replaced."""
    if step <= 0:
        raise ToolError("Шаг должен быть положительным числом секунд.")
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.iterdir():
        if SHEET.match(old.name):
            old.unlink()
    ffmpeg("-i", video, "-vf", "fps=1/{:g},scale=400:-2,tile={}x{}".format(step, cols, rows), "-q:v", "4", folder / "sheet-%02d.jpg",
           what="Листы приёмки")
    sheets = sorted(p for p in folder.iterdir() if SHEET.match(p.name))
    if not sheets:
        raise ToolError("Листы не получились: видео короче одного шага?")
    return sheets


def overview(video: Path, out: Path) -> Tuple[float, int]:
    """One sheet of 36 frames across the whole video, to choose the seconds worth taking."""
    step = max(1.0, round(duration_of(video) / 36))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + ".part" + out.suffix)
    ffmpeg("-skip_frame", "nokey", "-i", video, "-vf", "fps=1/{:g},scale=320:-2,tile=9x4".format(step), "-frames:v", "1", "-q:v", "4", tmp,
           what="Обзорный лист")
    os.replace(str(tmp), str(out))
    return step, 9


def parse_crop(text: Optional[str]) -> Tuple[float, float, float, float]:
    if not text:
        return 0.0, 0.0, 1.0, 1.0
    try:
        x, y, w, h = (float(v) for v in text.split(","))
    except ValueError:
        raise ToolError("--crop: четыре доли кадра через запятую «x,y,ширина,высота», например 0.11,0.09,0.655,0.84")
    if not (0 <= x < 1 and 0 <= y < 1 and 0 < w <= 1 and 0 < h <= 1 and x + w <= 1.001 and y + h <= 1.001):
        raise ToolError("--crop: доли должны лежать внутри кадра (0...1).")
    return x, y, w, h


def take_frames(video: Path, work: Path, label: str, seconds: List[str], crop: Tuple[float, float, float, float], width: int) -> List[Path]:
    """public/frames/<label>-<second>.jpg; src/data/frames.json remembers each aspect for the WorkFrame component."""
    info = probe(video)
    x, y, w, h = crop
    aspect = (info["width"] * w) / (info["height"] * h)
    label = re.sub(r"[^\w-]+", "-", label).strip("-") or "frame"
    folder = work / "public" / "frames"
    folder.mkdir(parents=True, exist_ok=True)
    index_path = work / "src" / "data" / "frames.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.is_file() else {}
    made = []
    for sec in seconds:
        if float(sec) > info["duration"]:
            raise ToolError("Секунда {} за пределами видео ({:.1f} с).".format(sec, info["duration"]))
        name = "{}-{}".format(label, sec)
        target = folder / (name + ".jpg")
        tmp = folder / (name + ".part.jpg")
        ffmpeg("-ss", sec, "-i", video, "-frames:v", "1", "-vf", "crop=iw*{}:ih*{}:iw*{}:ih*{},scale={}:-2".format(w, h, x, y, width), "-q:v", "2", tmp,
               what="Кадр на {} с".format(sec))
        os.replace(str(tmp), str(target))
        index[name] = round(aspect, 4)
        made.append(target)
    write_atomic(index_path, json.dumps(index, indent=1, sort_keys=True) + "\n")
    return made

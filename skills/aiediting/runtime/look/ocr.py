"""Text on frames: Apple Vision on macOS (through the system `swift`), Tesseract elsewhere.

AIEDITING_OCR=vision|tesseract|none forces the choice; AIEDITING_TESSERACT points at tesseract.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .errors import LookError

SCRIPT = Path(__file__).with_name("vision_ocr.swift")


def _quiet(cmd) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          encoding="utf-8", errors="replace", timeout=600)


def _vision_ok() -> bool:
    # Without Xcode tools `swift` opens an install dialog, so ask xcode-select first.
    if sys.platform != "darwin" or not shutil.which("swift") or not shutil.which("xcode-select"):
        return False
    return _quiet(["xcode-select", "-p"]).returncode == 0


def _tesseract() -> Optional[str]:
    return os.environ.get("AIEDITING_TESSERACT") or shutil.which("tesseract")


def ocr_backend() -> Optional[str]:
    """"vision", "tesseract" or None when nothing can read text on frames here."""
    forced = os.environ.get("AIEDITING_OCR")
    if forced:
        return None if forced == "none" else forced
    if _vision_ok():
        return "vision"
    return "tesseract" if _tesseract() else None


def _vision(paths: List[Path]) -> List[List[Dict]]:
    proc = _quiet(["swift", SCRIPT] + list(paths))
    if proc.returncode != 0:
        raise LookError("Apple Vision не прочитал кадры: {}".format(proc.stderr.strip()[-400:]))
    lines: List[List[Dict]] = [[] for _ in paths]
    for raw in proc.stdout.splitlines():
        item = json.loads(raw)
        rect = {k: int(round(item[k])) for k in ("x", "y", "w", "h")}
        lines[item["image"]].append({"text": item["text"], "rect": rect})
    return lines


def read_lines(paths, backend: Optional[str] = None) -> List[List[Dict]]:
    """For each frame: [{"text", "rect": {"x","y","w","h"}}], one item per line of text."""
    paths = [Path(p) for p in paths]
    backend = backend or ocr_backend()
    if backend == "vision":
        return _vision(paths)
    if backend == "tesseract":
        from .tesseract import read_tesseract
        return [read_tesseract(_tesseract() or "tesseract", p) for p in paths]
    raise LookError("Распознавание текста на кадрах недоступно: {}".format(backend))

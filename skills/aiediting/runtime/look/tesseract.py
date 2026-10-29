"""Tesseract OCR: words from its TSV output glued back into lines with their boxes."""
from __future__ import annotations

import functools
import subprocess
from pathlib import Path
from typing import Dict, List

from .errors import LookError


@functools.lru_cache(maxsize=4)
def _langs(exe: str) -> str:
    out = subprocess.run([exe, "--list-langs"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         encoding="utf-8", errors="replace").stdout
    have = {line.strip() for line in out.splitlines()}
    return "+".join(lang for lang in ("rus", "eng") if lang in have) or "eng"


def read_tesseract(exe: str, path: Path) -> List[Dict]:
    """[{"text", "rect"}] per line of text on one picture."""
    proc = subprocess.run([exe, str(path), "stdout", "-l", _langs(exe), "tsv"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          encoding="utf-8", errors="replace", timeout=300)
    if proc.returncode != 0:
        raise LookError("Tesseract не прочитал {}: {}".format(path, proc.stderr.strip()[-300:]))
    lines: Dict[tuple, Dict] = {}
    for row in proc.stdout.splitlines()[1:]:
        cols = row.split("\t")
        if len(cols) < 12 or cols[0] != "5" or not cols[11].strip():
            continue
        key = tuple(cols[1:5])
        x, y, w, h = (int(v) for v in cols[6:10])
        line = lines.setdefault(key, {"words": [], "x0": x, "y0": y, "x1": x + w, "y1": y + h})
        line["words"].append(cols[11].strip())
        line["x0"], line["y0"] = min(line["x0"], x), min(line["y0"], y)
        line["x1"], line["y1"] = max(line["x1"], x + w), max(line["y1"], y + h)
    return [{"text": " ".join(v["words"]),
             "rect": {"x": v["x0"], "y": v["y0"], "w": v["x1"] - v["x0"], "h": v["y1"] - v["y0"]}}
            for v in lines.values()]

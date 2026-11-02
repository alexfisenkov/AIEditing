"""Reading finished renders and scene sources: empty stretches and the text that appears on screen (needs numpy for empties)."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List, Tuple

from .audiosync import _np
from .common import ToolError

W, H, FPS = 160, 90, 4
DARK_SHARE = 0.42  # the stage fills most of the frame while a scene is active
EDGE_SHARE = 0.022  # a scene with content has fine structure outside the speaker's frame


def empty_stretches(video: Path, min_len: float) -> List[Tuple[float, float]]:
    np = _np()
    done = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(video), "-vf", "fps={},scale={}:{},format=gray".format(FPS, W, H), "-f", "rawvideo", "-"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if done.returncode != 0 or not done.stdout:
        raise ToolError("Не читается видео {}".format(video))
    frames = np.frombuffer(done.stdout, dtype=np.uint8).reshape(-1, H, W)
    flags = []
    for f in frames:
        dark = float((f < 62).mean())
        body = f[8:82].astype(int)
        edges = float((np.abs(np.diff(body, axis=1)) > 28).mean())
        flags.append(dark > DARK_SHARE and edges < EDGE_SHARE)
    found, t = [], 0
    while t < len(flags):
        if flags[t]:
            s = t
            while t < len(flags) and flags[t]:
                t += 1
            if (t - s) / FPS >= min_len:
                found.append((s / FPS, t / FPS))
        t += 1
    return found


_TEXT = re.compile(r">\s*([^<>{}\n]*[^\W\d_][^<>{}\n]*?)\s*<|\"([^\"\n]+)\"|'([^'\n]+)'")
_PLAIN = re.compile(r"^[^\W\d_][\w '’,.!?:;—–-]*$")  # words, not css values or identifiers with symbols


def _is_text(s: str) -> bool:
    if re.search(r"[A-Za-z]\d|\d[A-Za-z]", s):  # "M5 12.5l4.5": path data and sizes, not words
        return False
    if not _PLAIN.match(s):
        return any(ord(c) > 127 and c.isalpha() for c in s)  # non-ASCII words are text in any case
    return any(ord(c) > 127 for c in s) or (" " in s) or s[:1].isupper()


def screen_texts(scenes: Path, out: Path) -> int:
    """Every line of text the scenes put on screen, per file, for the language and fact critics."""
    rows, count = [], 0
    files = sorted(Path(scenes).glob("*.tsx"))
    if not files:
        raise ToolError("В {} нет файлов .tsx".format(scenes))
    for f in files:
        code = re.sub(r"/\*.*?\*/", "", f.read_text(encoding="utf-8"), flags=re.S)
        code = "\n".join(re.sub(r"(^|\s)//.*$", "", line) for line in code.splitlines())
        seen: List[str] = []
        for m in _TEXT.finditer(code):
            s = (m.group(1) or m.group(2) or m.group(3) or "").strip()
            if s and _is_text(s) and s not in seen:
                seen.append(s)
        count += len(seen)
        rows.append("## {}\n{}".format(f.name, "\n".join(seen)))
    Path(out).write_text("\n\n".join(rows) + "\n", encoding="utf-8")
    return count

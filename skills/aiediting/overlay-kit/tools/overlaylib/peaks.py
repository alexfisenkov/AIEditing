"""Sounds against movement: peaks of movement of a draft (difference of frames) and, for every cue of the scenes,
the nearest one and how many frames the sound's peak is off it. Seconds are seconds of the draft (the time map applied)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from .common import FPS, ToolError, say, work_dir

W, H = 32, 18          # a frame this small still shows where the picture moves, and reads fast
MIN_DIFF = 2.0         # mean change of a pixel (0–255) below which nothing moved
GAP = 0.2              # two peaks closer than this are one movement
NEAR = 1.0             # a peak of movement further than this from the sound is not its pair
_TUPLE = r'\[\s*(-?[\d.]+)\s*,\s*"([a-z0-9-]+)"\s*\]'
_OBJECT = r"\{([^{}]*\brole\s*:[^{}]*)\}"


def _frames(video: Path) -> List[bytes]:
    if not shutil.which("ffmpeg"):
        raise ToolError("Нет программы ffmpeg: без неё движение не измерить")
    done = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(video), "-vf",
                           "fps={},scale={}:{}:flags=area,format=gray".format(FPS, W, H), "-f", "rawvideo", "-"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if done.returncode != 0:
        raise ToolError("Видео {} не читается: {}".format(video, done.stderr.decode("utf-8", "replace").strip()[-200:]))
    size = W * H
    return [done.stdout[i:i + size] for i in range(0, len(done.stdout) - size + 1, size)]


def motion_curve(video: Path) -> List[float]:
    """Mean change of a pixel from the frame before, for every frame (the first is 0)."""
    frames = _frames(Path(video))
    return [0.0] + [sum(abs(a - b) for a, b in zip(cur, prev)) / float(W * H) for prev, cur in zip(frames, frames[1:])]


def motion_peaks(video: Path) -> List[float]:
    """Seconds where the picture changes most: local maxima well above the usual change of this video."""
    curve = motion_curve(video)
    if len(curve) < 3:
        return []
    ordered = sorted(curve)
    median = ordered[len(ordered) // 2]
    mad = sorted(abs(v - median) for v in curve)[len(curve) // 2]
    floor = max(MIN_DIFF, median + 4 * mad)
    found: List[int] = []
    for i in range(1, len(curve)):
        nxt = curve[i + 1] if i + 1 < len(curve) else -1.0
        if curve[i] >= floor and curve[i] >= curve[i - 1] and curve[i] > nxt:
            if found and (i - found[-1]) / FPS < GAP:
                if curve[i] > curve[found[-1]]:
                    found[-1] = i
                continue
            found.append(i)
    return [round(i / FPS, 3) for i in found]


def scene_cues(work: Path) -> List[Dict]:
    """[{t, name} | {t, role, n}] of every `cues` array in src/scenes/seg-*.tsx, in the order written."""
    cues: List[Dict] = []
    for path in sorted((work / "src" / "scenes").glob("seg-*.tsx")):
        text = path.read_text(encoding="utf-8")
        start = text.find("export const cues")
        if start < 0:
            continue
        body = text[text.find("[", text.find("=", start)):]
        depth, end = 0, len(body)
        for i, ch in enumerate(body):
            depth += 1 if ch == "[" else -1 if ch == "]" else 0
            if depth == 0:
                end = i
                break
        for m in re.finditer(_TUPLE + "|" + _OBJECT, body[1:end]):
            if m.group(1) is not None:
                cues.append({"t": float(m.group(1)), "name": m.group(2)})
                continue
            fields = m.group(3)
            role, at = re.search(r'\brole\s*:\s*"([a-z-]+)"', fields), re.search(r"\bat\s*:\s*(-?[\d.]+)", fields)
            n = re.search(r"\bn\s*:\s*(\d+)", fields)
            if role and at:
                cues.append({"t": float(at.group(1)), "role": role.group(1), "n": int(n.group(1)) if n else 0})
    return cues


def _to_new(work: Path, t: float) -> Optional[float]:
    path = work / "src" / "data" / "time-map.json"
    rows = json.loads(path.read_text(encoding="utf-8")).get("rows") if path.is_file() else []
    if not rows:
        return t
    for new_a, _new_b, old_a, old_b, lead in rows:
        if old_a <= t < old_b:
            return new_a + lead + (t - old_a)
    return None


def report(work: Path, draft: Path) -> List[Dict]:
    """[{t, sound, peak, motion, shift}] per cue; motion and shift are None when nothing moves within NEAR seconds."""
    data = json.loads((work / "src" / "data" / "sfx.json").read_text(encoding="utf-8"))
    files, roles = data.get("files") or {}, data.get("roles") or {}
    peak_of = {s["file"]: s.get("peak_ms", 0) for rows in roles.values() for s in rows}
    moves = motion_peaks(draft)
    out = []
    for cue in scene_cues(work):
        at = _to_new(work, cue["t"])
        if "role" in cue:
            have = roles.get(cue["role"]) or []
            sound = have[cue["n"] % len(have)] if have else None
            peak = at if sound is not None and at is not None else None
        else:
            sound = files.get(cue["name"])
            peak = at + peak_of.get(sound, 0) / 1000.0 if sound is not None and at is not None else None
        near = min(moves, key=lambda m: abs(m - peak), default=None) if peak is not None else None
        if near is not None and abs(near - peak) > NEAR:
            near = None
        out.append({"t": cue["t"], "sound": cue.get("role") or cue["name"], "peak": peak, "motion": near,
                    "shift": None if near is None else int(round((near - peak) * FPS))})
    return out


def _frames_word(n: int) -> str:
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return "кадр"
    return "кадра" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else "кадров"


def cmd_peaks(args) -> int:
    work, draft = work_dir(args.work), Path(args.draft).expanduser()
    if not draft.is_file():
        raise ToolError("Нет черновика {}: сначала overlay.py draft {}".format(draft, work))
    rows = report(work, draft)
    if not rows:
        say("В сценах нет ни одного звука (массивы cues пусты).")
    for r in rows:
        head = "{:7.2f} с  {:<12}".format(r["t"], r["sound"])
        if r["peak"] is None:
            say(head + " звука нет на диске или момент вырезан — в ролике его не будет")
        elif r["motion"] is None:
            say(head + " пик звука {:.2f} с — пика движения рядом нет".format(r["peak"]))
        else:
            say(head + " пик звука {:.2f} с → пик движения {:.2f} с, сдвиг {:+d} {}".format(
                r["peak"], r["motion"], r["shift"], _frames_word(r["shift"])))
    return 0

"""Measuring a finished vertical clip: format, lengths of the tracks, loudness, the tail, a hum, how long the call to action stands."""
from __future__ import annotations

import json
import re
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import vaudio, vspans
from .audiosync import _np
from .common import FPS, ToolError, ffmpeg_text

W, H = 1080, 1920
LUFS_TOLERANCE = 1.0
PEAK_LIMIT = -1.0  # the true peak must not be above this; the mix aims lower (vsound.MIX_PEAK) so the AAC overshoot stays inside
LENGTH_TOLERANCE = 0.1  # seconds: between the tracks, and against the length the data gives
TAIL_QUIET_DB = -60.0
SAMPLE_FPS = 10  # frames per second for the look at the call to action
STRIP_PX = 350  # the band over the card (the card starts at y 500): only the curtain lies there while the call stands
UNIFORM = 0.995  # share of the band's pixels near the curtain colour
NEAR = 3  # grey levels


def probe(path: Path) -> Dict:
    raw = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, universal_newlines=True, encoding="utf-8", errors="replace")
    try:
        info = json.loads(raw.stdout)
    except ValueError:
        raise ToolError("Файл не читается как видео: {}".format(path))
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    sound = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    if video is None or sound is None:
        raise ToolError("В файле {} нет {}.".format(path, "видео" if video is None else "звука"))
    fps = float(Fraction(video.get("r_frame_rate") or "0/1")) if video.get("r_frame_rate") not in (None, "0/0") else 0.0
    return {"width": int(video["width"]), "height": int(video["height"]), "fps": fps,
            "video": float(video.get("duration") or info["format"]["duration"]), "audio": float(sound.get("duration") or info["format"]["duration"]),
            "total": float(info["format"]["duration"])}


def loudness(path: Path) -> Tuple[Optional[float], Optional[float]]:
    """(integrated LUFS, true peak dBFS) of the first audio stream."""
    text = ffmpeg_text("-i", path, "-map", "0:a:0", "-af", "ebur128=peak=true", "-f", "null", "-")
    tail = text[text.rfind("Summary:"):] if "Summary:" in text else ""
    lufs = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    peak = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    return (float(lufs.group(1)) if lufs else None, float(peak.group(1)) if peak else None)


def call_seconds(path: Path) -> float:
    """How long the call to action stands fully on the screen at the end of the clip.

    The curtain is one flat colour over the whole frame. The band above the card (all x, y from 0 to 350) holds nothing else
    while the call stands, whatever colour the design's curtain has and however far the card's shadow reaches. Counted backwards
    from the last frame, at 10 frames a second.
    """
    np = _np()
    w, h = W // 10, H // 10
    done = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-vf", "fps={},scale={}:{},format=gray".format(SAMPLE_FPS, w, h), "-f", "rawvideo", "-"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if done.returncode != 0 or not done.stdout:
        raise ToolError("Не читается картинка файла {}.".format(path))
    frames = np.frombuffer(done.stdout, dtype=np.uint8).reshape(-1, h, w).astype(int)
    band = frames[:, : STRIP_PX // 10, :].reshape(len(frames), -1)
    ref = int(np.median(band[-1]))
    flat = (np.abs(band - ref) <= NEAR).mean(axis=1) >= UNIFORM
    run = 0
    for ok in flat[::-1]:
        if not ok:
            break
        run += 1
    return run / SAMPLE_FPS


def check_clip(path: Path, data: Dict, cid: str, lufs_target: float = -14.0, hum_accepted: Optional[str] = None) -> Tuple[bool, List[str]]:
    """(all well, lines for the person). A failed line begins with «НЕТ». `hum_accepted` is the reason the person gave for letting
    a hum finding pass: it then becomes a warning and is printed."""
    lines: List[str] = []
    ok = True

    def line(good: bool, text: str):
        nonlocal ok
        ok = ok and good
        lines.append(("есть " if good else "НЕТ ") + text)

    info = probe(path)
    want = vspans.clip_seconds(data, cid)
    line((info["width"], info["height"]) == (W, H) and abs(info["fps"] - FPS) < 0.01,
         "формат {}x{}, {:.2f} к/с (нужно {}x{}, {} к/с)".format(info["width"], info["height"], info["fps"], W, H, FPS))
    line(abs(info["video"] - info["audio"]) <= LENGTH_TOLERANCE,
         "длины дорожек равны: видео {:.2f} с, звук {:.2f} с".format(info["video"], info["audio"]))
    line(abs(info["video"] - want) <= LENGTH_TOLERANCE, "длина {:.2f} с, по данным должна быть {:.2f} с".format(info["video"], want))
    lufs, peak = loudness(path)
    line(lufs is not None and abs(lufs - lufs_target) <= LUFS_TOLERANCE and peak is not None and peak <= PEAK_LIMIT,
         "громкость {} LUFS, пик {} dBFS (нужно {:g} LUFS ±{:g}, пик не выше {:g})".format(
             "?" if lufs is None else lufs, "?" if peak is None else peak, lufs_target, LUFS_TOLERANCE, PEAK_LIMIT))
    x = vaudio.decode(path)
    speech_end = vspans.speech_seconds(data, cid)
    if vspans.tail(data) > 0:
        tail = vaudio.tail_peak_db(x, speech_end + 0.1)
        line(tail is not None and tail <= TAIL_QUIET_DB, "хвост после речи тихий ({} dBFS, нужно не выше {:g})".format("нет хвоста" if tail is None else "{:.1f}".format(tail), TAIL_QUIET_DB))
    start = vspans.cta_start(data, cid)
    quiet_until = max(1.0, start - 0.05) if start is not None and start > 3.0 else speech_end
    hum = vaudio.hum_report(x, quiet_until)
    for problem in hum["problems"]:
        if hum_accepted:
            lines.append("ПРЕДУПРЕЖДЕНИЕ гул пропущен по основанию «{}»: {}".format(hum_accepted, problem))
        else:
            line(False, "гул: " + problem)
    if not hum["problems"]:
        tone = "" if hum["tone_hz"] is None else ", самый сильный тон {:.0f} Гц на {:.0f} дБ над соседними".format(hum["tone_hz"], hum["tone_db"])
        lines.append("есть чистая речь: тихие места на {:.1f} дБ ниже речи{}".format(hum["gap_db"], tone))
    if vspans.has_cta(data):
        stood = call_seconds(path)
        need = vspans.cta_needed(data)
        line(stood + 0.15 >= need, "призыв стоит {:.1f} с (нужно не меньше {:.1f} с: {:g} до конца речи и {:g} после, минус появление)".format(
            stood, need, vspans.lead(data), vspans.tail(data)))
    else:
        lines.append("призыва в этом ролике нет (так задано в spans.json)")
    return ok, lines

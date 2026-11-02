"""Loudness: measure with loudnorm, then apply it in a second linear pass. Target and true peak are the person's choice."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict

from .common import ToolError, ffmpeg_text

TRUE_PEAK = -1.0
LRA = 11


def measure(path: Path, lufs: float) -> Dict[str, float]:
    text = ffmpeg_text("-i", path, "-map", "0:a:0", "-af", "loudnorm=I={:g}:TP={:g}:LRA={}:print_format=json".format(lufs, TRUE_PEAK, LRA), "-f", "null", "-")
    found = re.search(r"\{[^{}]*input_i[^{}]*\}", text, re.S)
    if not found:
        raise ToolError("Не удалось измерить громкость файла {}: нет звука?".format(path))
    data = json.loads(found.group(0))
    try:
        values = {k: float(data[k]) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}
    except (KeyError, ValueError):
        raise ToolError("Громкость файла {} не измерена (тишина?).".format(path))
    if values["input_i"] < -70:
        raise ToolError("В звуке рендера тишина (громкость {:.1f} LUFS): сводить нечего.".format(values["input_i"]))
    return values


def audio_filter(lufs: float, m: Dict[str, float], shift: float) -> str:
    """Remove the encoder delay (shift > 0 trims the start, < 0 pads it), then normalise with the measured values."""
    parts = []
    if shift > 0:
        parts.append("atrim=start={:.5f},asetpts=PTS-STARTPTS".format(shift))
    elif shift < 0:
        ms = int(round(-shift * 1000))
        parts.append("adelay={}|{}".format(ms, ms))
    parts.append("loudnorm=I={:g}:TP={:g}:LRA={}:measured_I={}:measured_TP={}:measured_LRA={}:measured_thresh={}:offset={}:linear=true".format(
        lufs, TRUE_PEAK, LRA, m["input_i"], m["input_tp"], m["input_lra"], m["input_thresh"], m["target_offset"]))
    return ",".join(parts)


def summary(path: Path) -> str:
    """Integrated loudness, loudness range and true peak of the finished file."""
    text = ffmpeg_text("-i", path, "-map", "0:a:0", "-af", "ebur128=peak=true", "-f", "null", "-")
    tail = text[text.rfind("Summary:"):] if "Summary:" in text else text[-600:]
    pick = lambda label: (re.search(label + r":\s+(-?[\d.]+)", tail) or [None, "?"])[1]  # noqa: E731
    return "громкость {} LUFS, диапазон {} LU, пик {} dBFS".format(pick("I"), pick("LRA"), pick("Peak"))

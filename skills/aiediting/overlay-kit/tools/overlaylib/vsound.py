"""The sound of a vertical clip: only the clean speech (public/clips/speech.wav), cut by the spans of the clip and sped up
by `rate`, a soft click where the call to action appears, a short fade at the end of the speech, silence in the tail,
loudness set in two passes. No pad underneath: this path has none yet."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from .common import ToolError, ffmpeg, ffmpeg_text
from .loudness import LRA

EDGE = 0.015  # fade of each cut edge, seconds: no click where two spans meet
END_FADE = 0.2  # fade at the end of the speech
CLICK_GAIN = 0.35
MIX_PEAK = -1.5  # the mix aims below the -1 dBFS the check allows: AAC overshoots a little after the limiter


def graph(spans: List[List[float]], rate: float, total: float, click_at: Optional[float]) -> List[str]:
    """filter_complex parts that end in [mix]: input 0 is the speech, input 1 (when `click_at` is given) the click."""
    parts, joined = [], []
    for i, (a, b) in enumerate(spans):
        d = b - a
        parts.append("[0:a]atrim=start={:.3f}:end={:.3f},asetpts=PTS-STARTPTS,afade=t=in:d={},afade=t=out:st={:.3f}:d={}[a{}]".format(
            a, b, EDGE, max(0.0, d - EDGE), EDGE, i))
        joined.append("[a{}]".format(i))
    speech = sum(b - a for a, b in spans) / rate
    parts.append("".join(joined) + "concat=n={}:v=0:a=1,atempo={:.4f},afade=t=out:st={:.3f}:d={},aformat=sample_rates=48000:channel_layouts=stereo,apad[speech]".format(
        len(spans), rate, max(0.0, speech - END_FADE), END_FADE))
    if click_at is None:
        parts.append("[speech]atrim=0:{:.3f}[mix]".format(total))
    else:
        parts.append("[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={},adelay={}:all=1[pop]".format(CLICK_GAIN, int(round(click_at * 1000))))
        parts.append("[speech][pop]amix=inputs=2:duration=first:normalize=0,atrim=0:{:.3f}[mix]".format(total))
    return parts


def _measure(inputs: List, parts: List[str], lufs: float) -> Dict[str, float]:
    text = ffmpeg_text(*sum((["-i", str(p)] for p in inputs), []), "-filter_complex",
                       ";".join(parts) + ";[mix]loudnorm=I={:g}:TP={:g}:LRA={}:print_format=json[o]".format(lufs, MIX_PEAK, LRA), "-map", "[o]", "-f", "null", "-")
    found = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", text, re.S)
    if not found:
        raise ToolError("Не удалось измерить громкость клипа: {}".format(text.strip()[-300:]))
    data = json.loads(found[-1])
    try:
        values = {k: float(data[k]) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}
    except (KeyError, ValueError):
        raise ToolError("Громкость клипа не измерена (в речи тишина?).")
    if values["input_i"] < -70:
        raise ToolError("В звуке клипа тишина (громкость {:.1f} LUFS): проверьте отрезки и public/clips/speech.wav.".format(values["input_i"]))
    return values


def mix(speech: Path, click: Optional[Path], silent: Path, spans: List[List[float]], rate: float, total: float, click_at: Optional[float],
        out: Path, lufs: float = -14.0) -> None:
    """The finished clip: the picture of `silent` untouched, the sound built from the speech."""
    use_click = click is not None and click.is_file() and click_at is not None
    parts = graph(spans, rate, total, click_at if use_click else None)
    inputs = [speech] + ([click] if use_click else [])
    m = _measure(inputs, parts, lufs)
    norm = ("[mix]loudnorm=I={:g}:TP={:g}:LRA={}:measured_I={}:measured_TP={}:measured_LRA={}:measured_thresh={}:offset={}:linear=true,"
            "aresample=48000,apad,atrim=0:{:.3f}[aout]").format(lufs, MIX_PEAK, LRA, m["input_i"], m["input_tp"], m["input_lra"],
                                                                  m["input_thresh"], m["target_offset"], total)
    args = sum((["-i", str(p)] for p in inputs), []) + ["-i", str(silent), "-filter_complex", ";".join(parts + [norm]),
                                                       "-map", "{}:v:0".format(len(inputs)), "-map", "[aout]", "-c:v", "copy",
                                                       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    ffmpeg(*args, what="Сведение звука клипа")

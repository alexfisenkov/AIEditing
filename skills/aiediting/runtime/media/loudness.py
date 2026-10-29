"""Loudness normalisation to a target LUFS: measure first, then apply linearly (two passes)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .ffmpeg import MediaError, ensure_file, run
from .probe import probe

TRUE_PEAK = -1.5
RANGE = 11
AUDIO_CODECS = {".wav": ["-c:a", "pcm_s16le"], ".flac": ["-c:a", "flac"]}


def _measure(src, lufs: float) -> dict:
    flt = "loudnorm=I={}:TP={}:LRA={}:print_format=json".format(lufs, TRUE_PEAK, RANGE)
    err = run(["-i", src, "-vn", "-af", flt, "-f", "null", "-"]).stderr
    found = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S)
    if not found:
        raise MediaError("loudnorm не вернул замер громкости для {}".format(src))
    return json.loads(found[-1])


def loudnorm(src, out, lufs: float = -16) -> Path:
    """Writes `out` with audio at `lufs` integrated loudness; video is copied untouched."""
    src, out = ensure_file(src), Path(out)
    info = probe(src)
    if not info["has_audio"]:
        raise MediaError("В файле нет звука: {}".format(src))
    m = _measure(src, lufs)
    flt = ("loudnorm=I={i}:TP={tp}:LRA={lra}:measured_I={mi}:measured_TP={mtp}:"
           "measured_LRA={mlra}:measured_thresh={mth}:offset={off}:linear=true").format(
        i=lufs, tp=TRUE_PEAK, lra=RANGE, mi=m["input_i"], mtp=m["input_tp"],
        mlra=m["input_lra"], mth=m["input_thresh"], off=m["target_offset"])
    video = ["-map", "0:v:0", "-c:v", "copy"] if info["has_video"] else []
    codec = AUDIO_CODECS.get(out.suffix.lower(), ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"])
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["-i", src] + video + ["-map", "0:a:0", "-af", flt, "-ar", "48000"] + codec + [out])
    return out

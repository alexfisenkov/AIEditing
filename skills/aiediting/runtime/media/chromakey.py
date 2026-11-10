"""Remove a chosen green/blue-screen colour locally with ffmpeg."""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from .ffmpeg import MediaError, ensure_file, run
from .probe import probe


def chromakey(src, out, key_color="#00ff00", similarity=0.12, blend=0.08) -> Path:
    src, out = ensure_file(src).resolve(), Path(out).expanduser().resolve()
    if src == out or out.suffix.lower() != ".mov":
        raise MediaError("Для прозрачного результата нужен отдельный .mov, исходник не меняется")
    if not isinstance(key_color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", key_color):
        raise MediaError("Цвет хромакея задаётся как #RRGGBB")
    similarity, blend = float(similarity), float(blend)
    if not 0.01 <= similarity <= 1 or not 0 <= blend <= 1:
        raise MediaError("similarity: 0.01–1, blend: 0–1")
    info = probe(src)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".aiediting-chromakey-", dir=str(out.parent)) as work:
        staged = Path(work) / "cutout.mov"
        run(["-i", src, "-map", "0:v:0", "-map", "0:a?", "-vf",
             "chromakey=0x{}:{:g}:{:g},format=yuva444p10le".format(key_color[1:], similarity, blend),
             "-c:v", "prores_ks", "-profile:v", "4", "-c:a", "aac", "-shortest", staged])
        got = probe(staged)
        if not got["has_video"] or (info["has_audio"] and not got["has_audio"]):
            raise MediaError("В результате потерялось видео или аудио")
        if abs(info["duration"] - got["duration"]) > max(0.15, info["duration"] * 0.005):
            raise MediaError("Хромакей изменил длительность видео")
        os.replace(str(staged), str(out))
    return out

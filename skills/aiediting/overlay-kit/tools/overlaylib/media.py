"""Probing a video and making the working copies: H.264 picture without sound, and the speech as WAV."""
from __future__ import annotations

import json
import os
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Dict, Optional

from .common import FPS, FRAME_H, FRAME_W, ToolError, ffmpeg, run, say, warn


def probe(path: Path) -> Dict:
    """Size (after rotation), fps, duration and whether there is sound."""
    if not Path(path).is_file():
        raise ToolError("Нет файла: {}".format(path))
    out = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(path)],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                         universal_newlines=True, encoding="utf-8", errors="replace").stdout
    try:
        data = json.loads(out or "")
    except ValueError:
        raise ToolError("Файл не читается как видео: {}".format(path))
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")), None)
    if video is None:
        raise ToolError("В файле нет видео: {}".format(path))
    width, height = int(video["width"]), int(video["height"])
    rotation = int(float(video.get("tags", {}).get("rotate", 0) or 0))
    for side in video.get("side_data_list", []):
        rotation = int(float(side.get("rotation", rotation) or 0))
    if abs(rotation) % 180 == 90:
        width, height = height, width
    fps = 0.0
    for key in ("avg_frame_rate", "r_frame_rate"):
        try:
            fps = float(Fraction(video.get(key) or "0/1"))
        except (ZeroDivisionError, ValueError):
            fps = 0.0
        if fps:
            break
    duration = float(data.get("format", {}).get("duration") or video.get("duration") or 0)
    return {
        "width": width, "height": height, "fps": fps, "duration": duration,
        "audio": any(s.get("codec_type") == "audio" for s in streams),
    }


def duration_of(path: Path) -> float:
    """Container duration of any media file (a WAV has no picture, so this is not probe())."""
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], "Длительность " + str(path)).stdout.strip()
    try:
        return float(out)
    except ValueError:
        raise ToolError("Не удалось узнать длительность: {}".format(path))


def check_16x9(info: Dict) -> None:
    if abs(info["width"] / info["height"] - 16 / 9) >= 0.02:
        raise ToolError("Кадр {}x{}, а наложения рассчитаны на 16:9. "
                        "Подготовьте запись 16:9 (в ролике 9:16 раскладки спикера не работают).".format(info["width"], info["height"]))
    if not info["audio"]:
        raise ToolError("В видео нет звука: без речи нечего сверять. Передайте запись со звуком.")


def _replace(tmp: Path, dst: Path) -> None:
    os.replace(str(tmp), str(dst))


def _identity(video: Path) -> Dict:
    st = video.stat()
    return {"size": st.st_size, "mtime": int(st.st_mtime)}


def make_copies(video: Path, info: Dict, work: Path) -> bool:
    """public/clips/source.mp4 (picture only, key frame every 15) and speech.wav. Done files are kept for the same
    video. Another video under the same folder (say, re-edited after a remark) replaces them: True then."""
    clips = work / "public" / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    source, speech = clips / "source.mp4", clips / "speech.wav"
    mark = work / "raw" / "source-id.json"
    replaced = False
    if source.is_file() and mark.is_file() and json.loads(mark.read_text(encoding="utf-8")) != _identity(video):
        track = work / "src" / "data" / "face.json"
        for stale in (source, speech, track, mark):  # all at once: a run cut short must not keep the old face track
            if stale.is_file():
                stale.unlink()
        replaced = True
        warn("это уже другое видео: копии, речь и трек лица сделаны заново. Сцены написаны под прежнее время, сверьте их секунды.")
    if source.is_file():
        have = probe(source)["duration"]
        if abs(have - info["duration"]) > 0.25:
            raise ToolError("В папке уже лежит другая запись ({:.2f} с против {:.2f} с). "
                            "Возьмите новую рабочую папку или удалите public/clips.".format(have, info["duration"]))
        say("Рабочая копия уже есть: " + str(source))
    else:
        filters = []
        if (info["width"], info["height"]) != (FRAME_W, FRAME_H):
            filters.append("scale={}:{}:flags=lanczos".format(FRAME_W, FRAME_H))
            say("Кадр {}x{} приведён к {}x{}.".format(info["width"], info["height"], FRAME_W, FRAME_H))
        if abs(info["fps"] - FPS) > 0.01:
            filters.append("fps={}".format(FPS))
            say("Частота кадров {:.3f} приведена к {}.".format(info["fps"], FPS))
        tmp = clips / "source.part.mp4"
        args = ["-i", video, "-map", "0:v:0", "-an"]
        if filters:
            args += ["-vf", ",".join(filters)]
        ffmpeg(*args, "-c:v", "libx264", "-preset", "medium", "-crf", "15", "-g", "15", "-pix_fmt", "yuv420p", tmp,
               what="Рабочая копия видео")
        _replace(tmp, source)
    if not speech.is_file():
        tmp = clips / "speech.part.wav"
        ffmpeg("-i", video, "-map", "0:a:0", "-c:a", "pcm_s16le", "-ar", "48000", tmp, what="Речь в WAV")
        _replace(tmp, speech)
    mark.parent.mkdir(parents=True, exist_ok=True)
    mark.write_text(json.dumps(_identity(video)), encoding="utf-8")
    return replaced

"""Local whisper.cpp (`whisper-cli`): free and private; one segment per word with `-ml 1 -sow`.

`model` is the path to a ggml model file. `command` (optional) replaces the program, e.g.
["C:/tools/whisper-cli.exe"]; AIEDITING_WHISPER_CLI does the same from the environment.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..media.audio import extract_audio
from ..media.ffmpeg import MediaError
from .contract import AsrError, make_transcript

_SPECIAL = re.compile(r"^\s*\[[^\]]*\]\s*$")   # [BLANK_AUDIO], [_BEG_] and the like


def _program(cfg: dict) -> list:
    if cfg.get("command"):
        return [str(p) for p in cfg["command"]]
    found = os.environ.get("AIEDITING_WHISPER_CLI") or shutil.which("whisper-cli")
    if not found:
        raise AsrError("Не найден whisper-cli. Поставьте whisper.cpp (macOS: brew install whisper-cpp; "
                       "Windows: сборка с github.com/ggml-org/whisper.cpp/releases) или выберите другой распознаватель.")
    return [found]


def transcribe(media: Path, cfg: dict) -> dict:
    model = Path(os.path.expanduser(str(cfg.get("model") or "")))
    if not cfg.get("model") or not model.is_file():
        raise AsrError("Не найден файл модели whisper: {}".format(model))
    language = cfg.get("language") or "auto"
    with tempfile.TemporaryDirectory(prefix="aiediting-asr-") as tmp:
        try:
            wav = extract_audio(media, Path(tmp) / "audio.wav")
        except MediaError as exc:
            raise AsrError(str(exc))
        prefix = Path(tmp) / "transcript"
        argv = _program(cfg) + ["-m", str(model), "-l", language, "-ml", "1", "-sow",
                                "-oj", "-np", "-of", str(prefix), str(wav)]
        try:
            proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as exc:
            raise AsrError("Не удалось запустить {}: {}".format(argv[0], exc.strerror))
        out = prefix.with_suffix(".json")
        if proc.returncode != 0 or not out.is_file():
            tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-3:]
            raise AsrError("whisper-cli завершился с ошибкой {}: {}".format(proc.returncode, " / ".join(tail)))
        data = json.loads(out.read_bytes().decode("utf-8", "replace"))
    words = [{"text": seg.get("text", ""), "start": seg["offsets"]["from"] / 1000.0,
              "end": seg["offsets"]["to"] / 1000.0}
             for seg in data.get("transcription", [])
             if seg.get("text", "").strip() and not _SPECIAL.match(seg.get("text", ""))]
    detected = (data.get("result") or {}).get("language")
    return make_transcript(words, cfg.get("language") or detected, "whispercpp")

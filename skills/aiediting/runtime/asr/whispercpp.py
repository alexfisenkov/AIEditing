"""Local whisper.cpp (`whisper-cli`): free and private; one segment per word with `-ml 1 -sow`.

`model` is the path to a ggml model file. `command` (optional) replaces the program, e.g.
["C:/tools/whisper-cli.exe"]; AIEDITING_WHISPER_CLI does the same from the environment.
`max_context` (optional) is whisper's `-mc`: 0 keeps a long recording from looping on one phrase.
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
_PHANTOMS = {"продолжение следует", "субтитры создавал", "субтитры сделал", "субтитры делал"}  # heard in silence
_CREDIT = re.compile(r"^[A-Za-z][\w.-]*$")      # the invented name that follows «субтитры создавал»


def _plain(word: dict) -> str:
    return re.sub(r"[^\w-]", "", str(word["text"]).lower())


def drop_phantoms(words: list) -> list:
    """Whisper was trained on subtitled films and writes their credits into silence, even over real speech."""
    out, i = [], 0
    while i < len(words):
        if " ".join(_plain(w) for w in words[i:i + 2]) in _PHANTOMS:
            i += 2
            if i < len(words) and _CREDIT.match(str(words[i]["text"]).strip()):
                i += 1
            continue
        out.append(words[i])
        i += 1
    return out


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
        context = [] if cfg.get("max_context") is None else ["-mc", str(int(cfg["max_context"]))]
        argv = _program(cfg) + ["-m", str(model), "-l", language, "-ml", "1", "-sow", *context,
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
    clean = drop_phantoms(words)
    result = make_transcript(clean, cfg.get("language") or detected, "whispercpp")
    if len(clean) != len(words):  # said aloud it would be lost silently, so the report names it
        result["phantoms"] = len(words) - len(clean)
    return result

"""The user's own recogniser: any program that prints (or writes) JSON with timed words.

`command` is a list; `{input}`, `{language}`, `{model}` and `{output}` are filled in. Without
`{output}` the JSON is read from stdout. Accepted shape: {"words": [{text|word, start, end, type?}],
"language"?} — the same shape as ElevenLabs Scribe or OpenAI verbose_json.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from .contract import AsrError, make_transcript


def _fill(part: str, values: dict) -> str:
    for key, value in values.items():
        part = part.replace("{" + key + "}", value)
    return part


def transcribe(media: Path, cfg: dict) -> dict:
    template = cfg.get("command") or []
    if not template:
        raise AsrError("Для поставщика command нужен список command: программа и её аргументы.")
    with tempfile.TemporaryDirectory(prefix="aiediting-asr-") as tmp:
        out = Path(tmp) / "transcript.json"
        values = {"input": str(media), "language": cfg.get("language") or "",
                  "model": cfg.get("model") or "", "output": str(out)}
        argv = [_fill(str(part), values) for part in template]
        try:
            proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as exc:
            raise AsrError("Не удалось запустить {}: {}".format(argv[0], exc.strerror))
        if proc.returncode != 0:
            tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-3:]
            raise AsrError("Команда распознавания завершилась с ошибкой {}: {}".format(
                proc.returncode, " / ".join(tail)))
        raw = out.read_bytes() if any("{output}" in str(p) for p in template) else proc.stdout
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except ValueError:
        raise AsrError("Команда распознавания вернула не JSON.")
    if not isinstance(data, dict) or not isinstance(data.get("words"), list):
        raise AsrError("В ответе команды нет списка words.")
    language = data.get("language") or data.get("language_code") or cfg.get("language")
    return make_transcript(data["words"], language, "command")

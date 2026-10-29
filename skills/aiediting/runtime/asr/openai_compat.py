"""Any OpenAI-compatible `/audio/transcriptions` endpoint: OpenAI, OpenRouter, a self-hosted server.

Key rules: `api_key_env` names the variable. With no `base_url` the default is OpenAI and its key
(`OPENAI_API_KEY`) is required; a custom `base_url` without `api_key_env` is called without a key.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from ..media.audio import extract_audio
from ..media.ffmpeg import MediaError
from .contract import AsrError, make_transcript
from .http import post_file
from .phrases import words_from_segments
from .secrets import read_key

DEFAULT_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "whisper-1"
DEFAULT_KEY_ENV = "OPENAI_API_KEY"


def transcribe(media: Path, cfg: dict) -> dict:
    key_env = cfg.get("api_key_env") or (None if cfg.get("base_url") else DEFAULT_KEY_ENV)
    key = read_key(key_env) if key_env else ""
    url = (cfg.get("base_url") or DEFAULT_URL).rstrip("/") + "/audio/transcriptions"
    fields = [("model", cfg.get("model") or DEFAULT_MODEL), ("response_format", "verbose_json"),
              ("timestamp_granularities[]", "word"), ("timestamp_granularities[]", "segment")]
    if cfg.get("language"):
        fields.append(("language", cfg["language"]))
    headers = {"Authorization": "Bearer " + key} if key else {}
    with tempfile.TemporaryDirectory(prefix="aiediting-asr-") as tmp:
        try:
            audio = extract_audio(media, Path(tmp) / "audio.m4a")
        except MediaError as exc:
            raise AsrError(str(exc))
        data = post_file(url, fields, "file", audio, headers, secret=key)
    words = data.get("words")
    if not isinstance(words, list) or not words:
        words = words_from_segments(data.get("segments") or [])
    if not words:
        raise AsrError("Сервис не вернул ни слов, ни фраз с временем — для монтажа нужно время слов.")
    return make_transcript(words, cfg.get("language") or data.get("language"), "openai_compat")

"""ElevenLabs Scribe: the most precise word boundaries; paid, the recording goes to the cloud."""
from __future__ import annotations

import tempfile
from pathlib import Path

from ..media.audio import extract_audio
from ..media.ffmpeg import MediaError
from .contract import AsrError, make_transcript
from .http import post_file
from .secrets import read_key

DEFAULT_URL = "https://api.elevenlabs.io"
DEFAULT_MODEL = "scribe_v2"
DEFAULT_KEY_ENV = "ELEVENLABS_API_KEY"


def transcribe(media: Path, cfg: dict) -> dict:
    key = read_key(cfg.get("api_key_env") or DEFAULT_KEY_ENV, cfg.get("key_file"))
    url = (cfg.get("base_url") or DEFAULT_URL).rstrip("/") + "/v1/speech-to-text"
    fields = [("model_id", cfg.get("model") or DEFAULT_MODEL),
              ("timestamps_granularity", "word"), ("tag_audio_events", "true")]
    if cfg.get("language"):
        fields.append(("language_code", cfg["language"]))
    with tempfile.TemporaryDirectory(prefix="aiediting-asr-") as tmp:
        try:
            audio = extract_audio(media, Path(tmp) / "audio.m4a")
        except MediaError as exc:
            raise AsrError(str(exc))
        data = post_file(url, fields, "file", audio, {"xi-api-key": key}, secret=key)
    if not isinstance(data.get("words"), list):
        raise AsrError("Scribe не вернул список слов.")
    language = cfg.get("language") or data.get("language_code")
    return make_transcript(data["words"], language, "scribe")

"""Speech recognition: four providers behind one call and one word format.

AsrConfig = {"provider": "whispercpp"|"scribe"|"openai_compat"|"command", "language": str,
             "model": str|None, "base_url": str|None, "api_key_env": str|None,
             "command": list[str]|None}
"""
from __future__ import annotations

import importlib
from pathlib import Path

from .contract import AsrError, is_filler, make_transcript
from .help import providers_help

PROVIDERS = ("whispercpp", "scribe", "openai_compat", "command")


def transcribe(media, cfg: dict) -> dict:
    """Returns Transcript = {"words": [...], "language": str, "provider": str}."""
    provider = (cfg or {}).get("provider")
    if provider not in PROVIDERS:
        raise AsrError("Неизвестный поставщик распознавания {!r}; доступны: {}.".format(
            provider, ", ".join(PROVIDERS)))
    media = Path(media)
    if not media.is_file():
        raise AsrError("Файл для распознавания не найден: {}".format(media))
    module = importlib.import_module("." + provider, __name__)
    return module.transcribe(media, cfg)


__all__ = ["AsrError", "PROVIDERS", "is_filler", "make_transcript", "providers_help", "transcribe"]

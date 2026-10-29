"""Pulling a mono speech track out of a video for recognisers."""
from __future__ import annotations

from pathlib import Path

from .ffmpeg import MediaError, ensure_file, run
from .probe import probe

_CODECS = {
    ".wav": ["-c:a", "pcm_s16le"],             # whisper.cpp wants 16 kHz PCM
    ".m4a": ["-c:a", "aac", "-b:a", "48k"],    # small upload, built into every ffmpeg
    ".flac": ["-c:a", "flac"],
}


def extract_audio(src, out, rate: int = 16000) -> Path:
    """Writes the first audio stream of `src` as mono `rate` Hz; the format follows `out`'s suffix."""
    src, out = ensure_file(src), Path(out)
    codec = _CODECS.get(out.suffix.lower())
    if codec is None:
        raise MediaError("Неподдерживаемый формат звука: {}".format(out.suffix))
    if not probe(src)["has_audio"]:
        raise MediaError("В файле нет звука: {}".format(src))
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["-i", src, "-map", "0:a:0", "-vn", "-ac", "1", "-ar", str(rate)] + codec + [out])
    return out

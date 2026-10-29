"""One word format for every recogniser.

Transcript = {"words": [{"text", "start", "end", "type": "word"|"spacing"|"filler"}],
              "language": str, "provider": str}
"""
from __future__ import annotations

import re
from typing import Iterable, List

# Hesitations that a lesson cut removes ("э-э", "м-м", "uh"); "ну" and "вот" stay words.
# Bare "мм"/"mm" stay words: they are also millimetres.
_FILLER = re.compile(r"^(э+(-э+)*|э+м+|м(-м+)+|м{3,}|хм+|uh+|um+|uhm+|erm|hm+|m(-m+)+|m{3,})$")


class AsrError(RuntimeError):
    """Recognition failed; the message is for a human and never contains a key."""


def is_filler(text: str) -> bool:
    core = re.sub(r"[\s.,!?…()\[\]]", "", text.lower()).replace("–", "-").replace("—", "-")
    return bool(core) and bool(_FILLER.match(core))


def word_type(text: str, raw_type: str = "word") -> str:
    if raw_type == "spacing" or (raw_type != "audio_event" and not text.strip()):
        return "spacing"
    return "filler" if is_filler(text) else "word"


def normalize_words(raw: Iterable[dict]) -> List[dict]:
    """Accepts {text|word, start, end, type?}; drops audio events that are not hesitations."""
    words = []
    for item in raw:
        text = str(item.get("text", item.get("word", "")))
        raw_type = str(item.get("type", "word"))
        kind = word_type(text, raw_type)
        if raw_type == "audio_event" and kind != "filler":
            continue
        try:
            start, end = float(item["start"]), float(item["end"])
        except (KeyError, TypeError, ValueError):
            raise AsrError("В ответе распознавателя у слова нет времени: {!r}".format(text))
        words.append({"text": text if kind == "spacing" else text.strip(),
                      "start": round(start, 3), "end": round(max(end, start), 3), "type": kind})
    words.sort(key=lambda w: (w["start"], w["end"]))
    return words


def make_transcript(raw_words: Iterable[dict], language: str, provider: str) -> dict:
    return {"words": normalize_words(raw_words), "language": language or "", "provider": provider}

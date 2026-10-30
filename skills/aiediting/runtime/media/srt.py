"""A sidecar `.srt` from a Transcript, with brand and term fixes from the profile glossary."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from .srt_lines import BREAK_GAP, MAX_CHARS, MAX_SECONDS, lines  # noqa: F401 (limits are re-exported)
from .srt_words import capital_after

_PUNCT = re.compile(r"^[\.,!?…:;»)\]]+$")


def _stamp(t: float) -> str:
    ms = int(round(max(t, 0.0) * 1000))
    return "{:02d}:{:02d}:{:02d},{:03d}".format(ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def _tokens(words: List[dict]) -> List[dict]:
    """Spoken words with their punctuation on them; a sentence starts with a capital letter."""
    tokens: List[dict] = []
    for w in words:
        text = str(w.get("text", "")).strip()
        if w.get("type", "word") != "word" or not text:
            continue
        if tokens and _PUNCT.match(text):
            tokens[-1]["text"] += text
            tokens[-1]["end"] = max(tokens[-1]["end"], float(w["end"]))
            continue
        if capital_after(tokens[-1]["text"] if tokens else "", text):
            text = text[:1].upper() + text[1:]
        tokens.append({"start": float(w["start"]), "end": float(w["end"]), "text": text})
    return tokens


def _cues(words: List[dict], glossary: Dict[str, str] = None) -> List[dict]:
    return lines(_tokens(words), glossary)


def _apply(text: str, glossary: Dict[str, str], index: int, start: float, fixes: List[dict]) -> str:
    for wrong, right in glossary.items():
        pattern = re.compile(r"(?<!\w){}(?!\w)".format(re.escape(wrong)), re.IGNORECASE)
        for m in pattern.finditer(text):
            if m.group(0) != right:
                fixes.append({"index": index, "start": start, "from": m.group(0), "to": right})
        text = pattern.sub(lambda _m: right, text)
    return text


def write_srt(transcript: dict, out, glossary: Dict[str, str] = None) -> List[dict]:
    """Writes `out` (UTF-8 .srt) and returns the fixes: [{index, start, from, to}]."""
    fixes: List[dict] = []
    blocks = []
    for i, cue in enumerate(_cues(transcript.get("words", []), glossary), start=1):
        text = _apply(cue["text"], glossary or {}, i, cue["start"], fixes)
        blocks.append("{}\n{} --> {}\n{}\n".format(i, _stamp(cue["start"]), _stamp(cue["end"]), text))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(str(out), "w", encoding="utf-8", newline="\n") as f:  # Path.write_text(newline=) needs 3.10
        f.write("\n".join(blocks))
    return fixes

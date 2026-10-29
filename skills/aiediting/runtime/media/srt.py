"""A sidecar `.srt` from a Transcript, with brand and term fixes from the profile glossary."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

MAX_CHARS = 42      # one comfortable subtitle line
MAX_SECONDS = 5.0
BREAK_GAP = 0.8     # a pause this long starts a new subtitle
_PUNCT = re.compile(r"^[\.,!?…:;»)\]]+$")


def _stamp(t: float) -> str:
    ms = int(round(max(t, 0.0) * 1000))
    return "{:02d}:{:02d}:{:02d},{:03d}".format(ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def _cues(words: List[dict]) -> List[dict]:
    cues: List[dict] = []
    for w in words:
        text = str(w.get("text", "")).strip()
        if w.get("type", "word") != "word" or not text:
            continue
        cur = cues[-1] if cues else None
        if cur and _PUNCT.match(text):
            cur["text"] += text
            cur["end"] = max(cur["end"], float(w["end"]))
            continue
        fresh = (cur is None or len(cur["text"]) + 1 + len(text) > MAX_CHARS
                 or float(w["end"]) - cur["start"] > MAX_SECONDS
                 or float(w["start"]) - cur["end"] > BREAK_GAP
                 or re.search(r"[.!?…]$", cur["text"]))
        if fresh:
            cues.append({"start": float(w["start"]), "end": float(w["end"]), "text": text})
        else:
            cur["text"] += " " + text
            cur["end"] = float(w["end"])
    return cues


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
    for i, cue in enumerate(_cues(transcript.get("words", [])), start=1):
        text = _apply(cue["text"], glossary or {}, i, cue["start"], fixes)
        blocks.append("{}\n{} --> {}\n{}\n".format(i, _stamp(cue["start"]), _stamp(cue["end"]), text))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(blocks), encoding="utf-8", newline="\n")
    return fixes

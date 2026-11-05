"""A sidecar `.srt` from a Transcript: one list of words, with the profile glossary and the person's corrections on it."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from .srt_fixes import corrected, glossed
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
    return lines(glossed(_tokens(words), glossary)[0], glossary)


def _final(words: List[dict], glossary: Dict[str, str] = None, corrections: Dict = None) -> Tuple[List[dict], List[dict], List[dict]]:
    """(the words as they go out, what changed, what to look at). The person corrects what they see, so the glossary goes first."""
    tokens, by_glossary = glossed(_tokens(words), glossary)
    tokens, by_person, missed = corrected(tokens, corrections)
    return tokens, by_glossary + by_person, missed


def final_tokens(words: List[dict], glossary: Dict[str, str] = None, corrections: Dict = None) -> List[dict]:
    """What is said as it goes to the person: the words file beside the `.srt` says the same as the `.srt`."""
    return _final(words, glossary, corrections)[0]


def missed_corrections(words: List[dict], glossary: Dict[str, str] = None, corrections: Dict = None) -> List[dict]:
    return _final(words, glossary, corrections)[2]


def write_srt(transcript: dict, out, glossary: Dict[str, str] = None, corrections: Dict = None) -> List[dict]:
    """Writes `out` (UTF-8 .srt) and returns the fixes: [{index, start, from, to}]."""
    tokens, changed, _ = _final(transcript.get("words", []), glossary, corrections)
    cues = lines(tokens, glossary)
    blocks = ["{}\n{} --> {}\n{}\n".format(i, _stamp(c["start"]), _stamp(c["end"]), c["text"]) for i, c in enumerate(cues, start=1)]
    fixes = [dict(row, index=next((i for i, c in enumerate(cues, start=1) if row["start"] < c["end"]), len(cues)))
             for row in sorted(changed, key=lambda c: c["start"])]
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(str(out), "w", encoding="utf-8", newline="\n") as f:  # Path.write_text(newline=) needs 3.10
        f.write("\n".join(blocks))
    return fixes

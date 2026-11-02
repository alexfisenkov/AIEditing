"""Burned-in captions for vertical video: short cues of a few words, drawn by the design layer."""
from __future__ import annotations

import re
from typing import Dict, List, Optional

MAX_WORDS, MAX_CHARS, GAP = 4, 24, 0.6


def _glossed(text: str, glossary: Dict[str, str]):
    """(the text with the glossary applied, [(from, to)] of what it changed)."""
    changes = []
    for wrong, right in glossary.items():
        pattern = re.compile(r"(?<!\w){}(?!\w)".format(re.escape(wrong)), re.IGNORECASE)
        changes += [(m.group(0), right) for m in pattern.finditer(text) if m.group(0) != right]
        text = pattern.sub(lambda _m: right, text)
    return text, changes


def cues(words: List[Dict], glossary: Dict[str, str], fixes: Optional[List[Dict]] = None) -> List[Dict]:
    """Cues of a few words; `fixes`, if given, gets each glossary change as the .srt lists it.

    As in the .srt a sentence starts with a capital letter: a cut leaves «все.» right before «в этом»."""
    from ..media.srt import _PUNCT
    from ..media.srt_words import capital_after

    out: List[Dict] = []
    last = ""
    for w in words:
        text = str(w.get("text", "")).strip()
        if w.get("type", "word") != "word" or not text:  # as the .srt: spacing, hesitations, sounds — out
            continue
        if _PUNCT.match(text):  # as the .srt: a mark on its own belongs to the word before it
            if out:
                out[-1].update(text=out[-1]["text"] + text, end=max(out[-1]["end"], w["end"]))
                last = out[-1]["text"]
            continue
        if last and capital_after(last, text):  # the first word may be the middle of a sentence: a clip starts anywhere
            text = text[:1].upper() + text[1:]
        text, changes = _glossed(text, glossary)
        last = text
        cur = out[-1] if out else None
        fresh = (cur is None or cur["n"] >= MAX_WORDS or len(cur["text"]) + 1 + len(text) > MAX_CHARS
                 or w["start"] - cur["end"] > GAP or re.search(r"[.!?…]$", cur["text"]))
        if fresh:
            out.append({"text": text, "start": w["start"], "end": w["end"], "n": 1})
        else:
            cur.update(text=cur["text"] + " " + text, end=w["end"], n=cur["n"] + 1)
        if fixes is not None:
            fixes += [{"index": len(out), "start": w["start"], "from": was, "to": now} for was, now in changes]
    for a, b in zip(out, out[1:]):  # hold a caption until the next one when the gap is small
        if b["start"] - a["end"] <= GAP:
            a["end"] = b["start"]
    return [{"kind": "caption", "text": c["text"], "start": c["start"], "end": max(c["end"], c["start"] + 0.3)}
            for c in out]


def burned(ctx, keep) -> List[Dict]:
    """Captions of a piece in output time. The glossary's fixes go to the report — unless the .srt step
    lists its own, or nothing is drawn."""
    from .words import mapped

    fixes: List[Dict] = []
    out = cues(mapped(ctx.transcript().get("words", []), keep), ctx.p("glossary", {}) or {}, fixes)
    if not ctx.has("write_srt") and (ctx.has("plate") or ctx.has("overlay_png")):
        ctx.report["fixes"] += fixes
    return out

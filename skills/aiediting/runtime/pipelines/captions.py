"""Burned-in captions for vertical video: short cues of a few words, drawn by the design layer."""
from __future__ import annotations

import re
from typing import Dict, List

MAX_WORDS, MAX_CHARS, GAP = 4, 24, 0.6


def cues(words: List[Dict], glossary: Dict[str, str]) -> List[Dict]:
    out: List[Dict] = []
    for w in words:
        if w.get("type") == "filler":
            continue
        text = str(w["text"]).strip()
        for wrong, right in glossary.items():
            text = re.sub(r"(?<!\w){}(?!\w)".format(re.escape(wrong)), right, text, flags=re.IGNORECASE)
        cur = out[-1] if out else None
        fresh = (cur is None or cur["n"] >= MAX_WORDS or len(cur["text"]) + 1 + len(text) > MAX_CHARS
                 or w["start"] - cur["end"] > GAP or re.search(r"[.!?…]$", cur["text"]))
        if fresh:
            out.append({"text": text, "start": w["start"], "end": w["end"], "n": 1})
        else:
            cur.update(text=cur["text"] + " " + text, end=w["end"], n=cur["n"] + 1)
    for a, b in zip(out, out[1:]):  # hold a caption until the next one when the gap is small
        if b["start"] - a["end"] <= GAP:
            a["end"] = b["start"]
    return [{"kind": "caption", "text": c["text"], "start": c["start"], "end": max(c["end"], c["start"] + 0.3)}
            for c in out]

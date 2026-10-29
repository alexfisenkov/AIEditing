"""Best stretches of a long video for 9:16: whole phrases only, scored by a plain rubric.

Rubric (10 points): hook at the start (question, number, strong word) 0–3; ends on a full stop 0–2;
speech density 0–2; length in the sweet spot 0–2; starts clean (no hesitation) 0–1.
"""
from __future__ import annotations

import re
from typing import Dict, List

from .words import norm, phrases, quote

HOOKS = {"почему", "как", "зачем", "секрет", "ошибка", "ошибки", "главное", "важно", "никогда", "всегда",
         "смотрите", "лайфхак", "бесплатно", "быстро", "why", "how", "secret", "mistake", "never"}


def _score(ph: List[Dict]) -> Dict:
    first, text = ph[0], " ".join(p["text"] for p in ph)
    words = [w for p in ph for w in p["words"]]
    dur = ph[-1]["end"] - ph[0]["start"]
    keys = {norm(w["text"]) for w in first["words"]}
    hook = int(first["text"].rstrip().endswith("?")) + int(bool(re.search(r"\d", first["text"]))) \
        + int(bool(keys & HOOKS))
    rate = len(words) / max(dur, 0.1)
    parts = {"hook": min(3, hook), "ending": 2 if re.search(r"[.!?…]$", text.strip()) else 0,
             "density": 2 if rate >= 2.0 else (1 if rate >= 1.4 else 0),
             "length": 2 if 20 <= dur <= 45 else 1, "clean": int(words[0].get("type") != "filler")}
    return dict(parts, total=sum(parts.values()))


def candidates(words: List[Dict], max_s: float = 60.0, min_s: float = 15.0, most: int = 10) -> List[Dict]:
    """[{id, start, end, score, why, said}], best first, not overlapping; borders at phrase ends."""
    ph = phrases(words)
    found = []
    for i in range(len(ph)):
        best = None
        for j in range(i, len(ph)):
            dur = ph[j]["end"] - ph[i]["start"]
            if dur > max_s:
                break
            if dur >= min_s:
                s = _score(ph[i:j + 1])
                if best is None or s["total"] > best[0]["total"]:
                    best = (s, j)
        if best:
            found.append({"start": ph[i]["start"], "end": ph[best[1]]["end"], "score": best[0]["total"],
                          "why": best[0], "said": quote(ph[i]["words"])})
    chosen: List[Dict] = []
    for c in sorted(found, key=lambda c: (-c["score"], c["start"])):
        if all(c["end"] <= o["start"] or c["start"] >= o["end"] for o in chosen):
            chosen.append(c)
        if len(chosen) == most:
            break
    return [dict(c, id="c{:02d}".format(k + 1)) for k, c in enumerate(chosen)]

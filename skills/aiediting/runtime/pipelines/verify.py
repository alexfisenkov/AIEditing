"""Second listening: the finished video is recognised again and compared with the words meant to stay."""
from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List

from .words import mapped, norm, recognise, spoken

HEARD_ALIKE = 0.6


def lost_words(expected: List[Dict], heard: List[Dict]) -> List[Dict]:
    a = [norm(w["text"]) for w in expected]
    b = [norm(w["text"]) for w in heard]
    lost = []
    for tag, i0, i1, j0, j1 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag not in ("delete", "replace"):
            continue
        for k in range(i0, i1):  # heard a little differently («отставляем»/«отправляем») is still heard
            if not any(SequenceMatcher(None, a[k], b[j]).ratio() >= HEARD_ALIKE for j in range(j0, j1)):
                lost.append({"text": expected[k]["text"], "at": expected[k]["start"]})
    return lost


def check_words(ctx, video: Path, keep) -> List[Dict]:
    """Words that survived the plan (hesitations aside) but are not heard in `video`."""
    expected = [w for w in mapped(spoken(ctx.transcript()), keep) if w.get("type") != "filler"]
    heard = [w for w in spoken(recognise(ctx, video, ctx.p("verify_asr"))) if w.get("type") != "filler"]
    return lost_words(expected, heard)

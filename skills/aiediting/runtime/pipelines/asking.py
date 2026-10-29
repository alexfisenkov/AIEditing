"""The approval point: one question with a key, JSON-safe data, and the person's (possibly edited) answer."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple


def json_safe(value):
    """Paths become strings, tuples lists: what `вопросы.json` can hold."""
    return json.loads(json.dumps(value, ensure_ascii=False, default=lambda o: str(o) if isinstance(o, Path)
                                 else repr(o)))


def ask(ctx, key: str, question: str, payload: Dict) -> Tuple[bool, Dict]:
    """approve(key, payload) -> bool; the approver may edit the payload in place (corrections)."""
    data = json_safe(dict(payload, key=key, question=question))
    ok = bool(ctx.approve(key, data))
    ctx.decisions.append({"key": key, "question": question, "ok": ok})
    return ok, data

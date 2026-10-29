"""Chapters: proposed at phrase starts every few minutes, titled by the person (or their agent)."""
from __future__ import annotations

from typing import Dict, List

from .words import phrases, quote, spoken

EVERY = 180.0  # seconds between proposed chapter starts


def _settings(ctx) -> Dict:
    raw = ctx.p("chapters")
    if raw is True:
        return {"plates": True, "timecodes": True}
    return dict(raw) if isinstance(raw, dict) else {}


def candidates(ctx, every: float) -> List[Dict]:
    found, last = [], None
    for p in phrases(spoken(ctx.transcript())):
        if last is None or p["start"] - last >= every:
            found.append({"start": round(p["start"], 3), "title": quote(p["words"], 6).rstrip(" …").rstrip(".,!?;:"),
                          "said": quote(p["words"])})
            last = p["start"]
    return found


def plan_chapters(ctx) -> None:
    s = _settings(ctx)
    if not (s.get("plates") or s.get("timecodes")):
        return
    items = candidates(ctx, float(s.get("every", EVERY)))
    if not items:
        return
    ok, data = ctx.ask("chapters", "Главы: поправьте title (коротко, 2–5 слов) и start; лишние уберите.",
                       {"items": items})
    if not ok:
        return
    chosen = sorted(data.get("items", []), key=lambda c: float(c["start"]))
    ctx.chapters = chosen
    if s.get("plates"):
        secs = float(s.get("seconds", ctx.design()["video"]["chapter"].get("seconds", 3.0)))
        ctx.overlays += [{"kind": "chapter", "text": c["title"], "start": float(c["start"]),
                          "end": float(c["start"]) + secs} for c in chosen if str(c.get("title", "")).strip()]

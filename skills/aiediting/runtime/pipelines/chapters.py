"""Chapters: proposed at phrase starts every few minutes, titled by the person (or their agent)."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .timeline import Span, to_out
from .words import phrases, quote, spoken

EVERY = 180.0  # seconds between proposed chapter starts
SPARE = 0.5    # a chapter plate keeps the screen to itself this much longer than it is shown


def _settings(ctx) -> Dict:
    raw = ctx.p("chapters")
    if raw is True:
        return {"plates": True, "timecodes": True}
    return dict(raw) if isinstance(raw, dict) else {}


def kept_start(t: float, keep: Sequence[Span]) -> float:
    """A chapter start that fell into a cut moves to the first kept moment after it (after all of them: the last kept one)."""
    t = float(t)
    if not keep or to_out(t, keep) is not None:
        return t
    after = [a for a, _b in keep if a > t]
    return float(min(after)) if after else float(max(b for _a, b in keep))


def out_at(t: float, keep: Sequence[Span]) -> Optional[float]:
    """Where a chapter starting at source second `t` begins in the cut video (a start in a cut: right after the cut)."""
    return to_out(kept_start(t, keep), keep) if keep else None


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
    keep = getattr(ctx, "keep", None) or []
    chosen = sorted((dict(c, start=kept_start(c["start"], keep)) for c in data.get("items", [])),
                    key=lambda c: float(c["start"]))
    ctx.chapters = chosen
    if s.get("plates"):
        secs = float(s.get("seconds", ctx.design()["video"]["chapter"].get("seconds", 3.0)))
        ctx.overlays += [{"kind": "chapter", "text": c["title"], "start": float(c["start"]),
                          "end": float(c["start"]) + secs} for c in chosen if str(c.get("title", "")).strip()]


def plate_windows(ctx) -> List[Dict]:
    """Where a chapter plate is on screen (source time, with a little spare): [{start, end, title}]."""
    return [{"start": o["start"], "end": o["end"] + SPARE, "title": o["text"]}
            for o in ctx.overlays if o.get("kind") == "chapter"]

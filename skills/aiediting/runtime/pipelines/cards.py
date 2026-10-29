"""Graphics as cards: slots at what is said, filled with text by the person; placed by the layout rule."""
from __future__ import annotations

from typing import Dict, List, Optional

from .words import phrases, quote, spoken

WINDOW = 15.0


def _density(ctx) -> int:
    per = ctx.p("graphics_per_15s")
    if isinstance(per, (list, tuple)) and per:
        return int(per[-1])
    return int(per) if per else 2


def wanted(ctx) -> bool:
    return bool(ctx.p("cards") or ctx.p("graphics_per_15s"))


def where(ctx, frame) -> Optional[str]:
    """The layout rule: over a screen — small in the corner opposite the face (or as the profile says)."""
    from ..render import opposite_corner

    rule = (ctx.p("cards") if isinstance(ctx.p("cards"), dict) else {}).get("on_screen", "corner")
    layout = ctx.layout or {}
    if layout.get("kind") in ("screen_face_window", "screen_only"):
        if rule == "none":
            return "none"
        if rule == "corner" and layout.get("face"):
            return opposite_corner(layout["face"], frame)
        return rule if rule in ("top", "center") else "top"
    return None  # the design's own place


def plan_cards(ctx) -> None:
    if not wanted(ctx):
        return
    slots: List[Dict] = []
    for p in phrases(spoken(ctx.transcript())):
        same = [s for s in slots if p["start"] - s["start"] < WINDOW]
        if len(same) < _density(ctx) and (not slots or p["start"] - slots[-1]["start"] >= WINDOW / 2):
            slots.append({"start": round(p["start"], 3), "end": round(p["start"] + 4.0, 3), "text": "",
                          "said": quote(p["words"])})
    if not slots:
        return
    ok, data = ctx.ask("cards", "Графика: впишите text («Заголовок\\nпояснение») в нужные слоты, "
                       "пустые не показываются. Не больше {} на 15 с.".format(_density(ctx)), {"items": slots})
    if ok:
        ctx.overlays += [{"kind": "card", "text": s["text"], "start": float(s["start"]), "end": float(s["end"])}
                         for s in data.get("items", []) if str(s.get("text", "")).strip()]

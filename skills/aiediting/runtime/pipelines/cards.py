"""Graphics as cards: slots at what is said, filled with text by the person; placed by the layout rule."""
from __future__ import annotations

from typing import Dict, List, Optional

from .chapters import plate_windows
from .kept import kept_phrases
from .report import stamp
from .words import norm, quote

WINDOW = 15.0


def _density(ctx) -> int:
    per = ctx.p("graphics_per_15s")
    if isinstance(per, (list, tuple)) and per:
        return int(per[-1])
    return int(per) if per else 2


def wanted(ctx) -> bool:
    return bool(ctx.p("cards") or ctx.p("graphics_per_15s"))


def where(ctx, frame, piece_layout: Optional[Dict] = None) -> Optional[str]:
    """The layout rule: over a screen — small in the corner opposite the face (or as the profile says).

    A 9:16 piece is judged by its own layout, in the finished frame `frame`, not by the source's.
    """
    from ..render import opposite_corner

    rule = (ctx.p("cards") if isinstance(ctx.p("cards"), dict) else {}).get("on_screen", "corner")
    if piece_layout:
        from ..media.vertical import shown_size
        from .placement import face_in_vertical

        if rule == "none" and piece_layout.get("kind") == "stack":
            return "none"
        face = face_in_vertical(piece_layout, shown_size(ctx.info), frame)
        return opposite_corner(face, frame) if face else None
    layout = ctx.layout or {}
    if layout.get("kind") in ("screen_face_window", "screen_only"):
        if rule == "none":
            return "none"
        if rule == "corner" and layout.get("face"):
            return opposite_corner(layout["face"], frame)
        return rule if rule in ("top", "center") else "top"
    return None  # the design's own place


def _plate_over(start: float, end: float, plates: List[Dict]) -> Optional[Dict]:
    return next((w for w in plates if start < w["end"] and end > w["start"]), None)


def _title(text: str) -> str:
    """First line of a card, compared without case and punctuation."""
    return norm(str(text).strip().split("\n")[0]).replace("-", "")


def _same_as_chapter(card: Dict, plates: List[Dict]) -> Optional[Dict]:
    """The chapter plate this card repeats: on screen at the same time, or titled like it."""
    own = _title(card["text"])
    return _plate_over(card["start"], card["end"], plates) or next(
        (w for w in plates if own and own == _title(w["title"])), None)


def drop_chapter_cards(ctx, cards: List[Dict]) -> List[Dict]:
    """A chapter title is shown by the chapter plate only: a card repeating it is taken off, with a note."""
    plates, kept = plate_windows(ctx), []
    for c in cards:
        plate = _same_as_chapter(c, plates) if plates else None
        if plate is None:
            kept.append(c)
            continue
        ctx.note("Карточка «{}» ({}) снята: совпала с главой «{}» — заголовок главы показывает только плашка"
                 .format(c["text"].strip().split("\n")[0], stamp(c["start"]), plate["title"]))
    return kept


def plan_cards(ctx) -> None:
    if not wanted(ctx):
        return
    slots: List[Dict] = []
    plates = plate_windows(ctx)  # no slots while a chapter plate is on screen
    for p in kept_phrases(ctx):  # only speech that stays: not a cut take, not a pause
        same = [s for s in slots if p["start"] - s["start"] < WINDOW]
        if len(same) < _density(ctx) and (not slots or p["start"] - slots[-1]["start"] >= WINDOW / 2):
            if _plate_over(p["start"], p["start"] + 4.0, plates):
                continue
            slots.append({"start": round(p["start"], 3), "end": round(p["start"] + 4.0, 3), "text": "",
                          "said": quote(p["words"])})
    if not slots:
        return
    ok, data = ctx.ask("cards", "Графика: впишите text («Заголовок\\nпояснение») в нужные слоты, "
                       "пустые не показываются. Не больше {} на 15 с.".format(_density(ctx)), {"items": slots})
    if ok:
        cards = [{"kind": "card", "text": s["text"], "start": float(s["start"]), "end": float(s["end"])}
                 for s in data.get("items", []) if str(s.get("text", "")).strip()]
        ctx.overlays += drop_chapter_cards(ctx, cards)

"""The `animations` step: inserts at what is said, approved by the person (anim_slots finds the moments).

An insert takes a card's place: a card at the same moment is taken off (one thing on screen at a time);
an insert never lands on a chapter plate (the chapter title is shown by the plate only).
"""
from __future__ import annotations

from typing import Dict, List

from ..render.anim_spec import template_file, template_id
from .anim_slots import every, length, over, slots
from .chapters import plate_windows
from .report import stamp

TEMPLATES = ["файлы", "шаги", "список", "число"]


def _chosen(ctx, answer: List[Dict]) -> List[Dict]:
    plates, out = plate_windows(ctx), []
    for s in answer:
        points = [str(i).strip() for i in s.get("items", []) if str(i).strip()]
        if not (points or str(s.get("title", "")).strip()):
            continue
        start = float(s["start"])
        end = float(s.get("end") or 0)
        end = end if end > start + 1.0 else start + length(ctx, s)
        plate, why = over(start, end, plates), None
        if template_id(s.get("template")) is None:
            why = "нет шаблона «{}»".format(s.get("template"))
        elif plate:
            why = "на этом месте плашка главы «{}»".format(plate["title"])
        if why:
            ctx.note("Анимация {} снята: {}".format(stamp(start), why))
            continue
        out.append({"kind": "animation", "template": s.get("template"), "title": str(s.get("title", "")).strip(),
                    "items": points, "text": ", ".join(points), "start": start, "end": end})
    return out


def _instead_of_cards(ctx, inserts: List[Dict]) -> None:
    kept = []
    for o in ctx.overlays:
        hit = over(o["start"], o["end"], inserts) if o.get("kind") == "card" else None
        if hit is None:
            kept.append(o)
            continue
        ctx.note("Карточка «{}» ({}) снята: в этот момент анимация «{}»".format(
            o["text"].split("\n")[0], stamp(o["start"]), hit["template"]))
    ctx.overlays = kept + inserts


def plan_animations(ctx) -> None:
    from ..render import hyperframes

    why = hyperframes.missing()
    if not why and template_file(ctx.design(), TEMPLATES[0]) is None:
        why = "в дизайн-системе формата нет шаблонов (design/animations/)"
    if why:
        ctx.note("Анимации не делались: " + why)
        return
    found = slots(ctx)
    if not found:
        return
    ok, data = ctx.ask("animations", "Анимации: поправьте template ({}), title и items (пункты), start; лишние "
                       "уберите. Пустой список — без анимаций.".format(" · ".join(TEMPLATES)),
                       {"items": found, "templates": TEMPLATES, "every": every(ctx)})
    if ok:
        _instead_of_cards(ctx, _chosen(ctx, data.get("items", [])))

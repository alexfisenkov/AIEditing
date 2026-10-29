"""The `animations` step: inserts at what is said, approved by the person (anim_slots finds the moments).

An insert takes a card's place: a card at the same moment is taken off (one thing on screen at a time);
an insert never lands on a chapter plate (the chapter title is shown by the plate only), nor on another.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..render.anim_spec import template_file, template_id
from .anim_answer import points, seconds, span
from .anim_slots import every, length, over, slots
from .chapters import plate_windows
from .report import stamp

TEMPLATES = ["файлы", "шаги", "список", "число"]


def _why_not(ctx, s: Dict, start: float, end: float, taken: List[Dict]) -> Optional[str]:
    plate, other = over(start, end, plate_windows(ctx)), over(start, end, taken)
    if template_id(s.get("template")) is None:
        return "нет шаблона «{}»".format(s.get("template"))
    if plate:
        return "на этом месте плашка главы «{}»".format(plate["title"])
    if other:
        return "пересекается с анимацией {}".format(stamp(other["start"]))
    return None


def _chosen(ctx, answer: List[Dict]) -> List[Dict]:
    out: List[Dict] = []
    for s in sorted(answer, key=lambda s: seconds(s.get("start")) or 0.0):
        said = points(s.get("items"))
        if not (said or str(s.get("title", "")).strip()):
            continue
        times, why = span(s, length(ctx, {"items": said}))
        why = why or _why_not(ctx, s, times[0], times[1], out)
        if why:
            ctx.note("Анимация «{}» ({}) снята: {}".format(s.get("template"), s.get("start"), why))
            continue
        out.append({"kind": "animation", "template": s.get("template"), "title": str(s.get("title", "")).strip(),
                    "items": said, "text": ", ".join(said), "start": times[0], "end": times[1]})
    return sorted(out, key=lambda o: o["start"])


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
    from ..render.hf_ready import problem

    why = problem()
    if not why and template_file(ctx.design(), TEMPLATES[0]) is None:
        why = "в дизайн-системе формата нет шаблонов (design/animations/)"
    if why:
        ctx.note("Анимации не делались: " + why)
        return
    found = slots(ctx)
    if not found:
        return
    ok, data = ctx.ask("animations", "Анимации: поправьте template ({}), title и items (пункты), start "
                       "(секунды или 0:01:23); лишние уберите. Пустой список — без анимаций.".format(
                           " · ".join(TEMPLATES)), {"items": found, "templates": TEMPLATES, "every": every(ctx)})
    if ok:
        _instead_of_cards(ctx, _chosen(ctx, data.get("items", [])))

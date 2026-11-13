"""Several cameras (step `angles`): line them up by sound and plan which angle the viewer sees when.

The main camera mostly; its crop ×1.2 about a quarter of the time in shots of 3–12 s, kept high so there is air above
the head; a side camera now and then for 3–10 s, never twice within a minute; a barely visible push-in at the start.
An angle changes only where speech was cut or a phrase ends, and none is shorter than 3 s. One camera: crop and push.
Times of the program are seconds of the cut video, before `params.speed`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .timeline import Span, length, merge, to_out

SHORTEST = 3.0
CROP = (3.0, 12.0, 6.0)   # shortest, longest, aimed at
SIDE = (3.0, 10.0, 5.0)
SIDE_EVERY = 60.0         # s between the starts of two side shots
SIDE_FIRST = 20.0         # s of the main camera before the first side shot
SHARE = 0.25              # of the time in the crop
ZOOM, HIGH = 1.2, 0.3     # the crop, and where it sits: 0 top … 0.5 middle of the room left
PUSH = 1.04               # the opening ends this much closer than it starts
_EPS = 1e-6


def _ends(points: Sequence[float], t: float, lo: float, hi: float, total: float) -> List[float]:
    """Where a shot from t may end: a point lo..hi after t that leaves a whole shot after it, or the very end."""
    found = [p for p in points if t + lo - _EPS <= p <= t + hi + _EPS and total - p >= SHORTEST - _EPS]
    return found + ([total] if t + lo - _EPS <= total <= t + hi + _EPS else [])


def _near(ends: List[float], aim: float) -> Optional[float]:
    return min(ends, key=lambda p: (abs(p - aim), p)) if ends else None


def _covers(spans: Sequence[Span], a: float, b: float) -> bool:
    return any(x - 1e-3 <= a and b <= y + 1e-3 for x, y in spans)


def program(total: float, points: Sequence[float], cameras: int = 1, cover: Optional[Dict[int, List[Span]]] = None) -> List[Dict]:
    """[{start, end, camera, crop}] over 0…total; camera 0 is the main one; `cover` = where camera N has picture."""
    points = sorted({round(float(p), 3) for p in points if SHORTEST <= float(p) <= total - SHORTEST})
    cover, plan = cover or {}, []
    t, cropped, last_side, n_side = 0.0, 0.0, None, 0
    while t < total - _EPS:
        aim = max(t + SHORTEST, 4 * (cropped + CROP[2]) - CROP[2])  # after the next crop a quarter is cropped
        end = _near(_ends(points, t, SHORTEST, total, total), aim) or total
        crop = {"zoom": 1.0, "to": PUSH, "y": HIGH} if not plan else None
        plan.append({"start": t, "end": end, "camera": 0, "crop": crop})
        t = end
        cam = 1 + n_side % max(1, cameras - 1)
        due = cameras > 1 and (t >= SIDE_FIRST if last_side is None else t - last_side >= SIDE_EVERY)
        ends = [p for p in _ends(points, t, SIDE[0], SIDE[1], total) if _covers(cover.get(cam, [(0.0, total)]), t, p)]
        if due and ends:
            end = _near(ends, t + SIDE[2])
            plan.append({"start": t, "end": end, "camera": cam, "crop": None})
            last_side, n_side, t = t, n_side + 1, end
            continue
        end = _near(_ends(points, t, CROP[0], CROP[1], total), t + CROP[2])
        if end is not None and t < total - _EPS:
            plan.append({"start": t, "end": end, "camera": 0, "crop": {"zoom": ZOOM, "y": HIGH}})
            cropped, t = cropped + end - t, end
    return _joined(plan)


def _joined(plan: List[Dict]) -> List[Dict]:
    """Two wide shots of the main camera in a row are one shot."""
    out: List[Dict] = []
    for s in plan:
        if out and s["camera"] == 0 and out[-1]["camera"] == 0 and s["crop"] is None and out[-1]["crop"] is None:
            out[-1]["end"] = s["end"]
        else:
            out.append(dict(s))
    return [dict(s, start=round(s["start"], 3), end=round(s["end"], 3)) for s in out]


def change_points(ctx) -> List[float]:
    """Seconds of the cut video where an angle may change: every seam of the cut, every pause between phrases."""
    from .words import phrases, spoken

    keep, out, passed = ctx.keep, [], 0.0
    for a, b in keep[:-1]:
        passed += b - a
        out.append(passed)
    said = phrases(spoken(ctx.transcript()))
    for one, nxt in zip(said, said[1:]):
        t = to_out((one["end"] + nxt["start"]) / 2.0, keep)
        if t is not None:
            out.append(t)
    return sorted(out)


def covered(keep: Sequence[Span], shift: float, duration: float) -> List[Span]:
    """Seconds of the cut video a file started `shift` s after the source and `duration` s long has picture for."""
    inside = [(max(a, shift), min(b, shift + duration)) for a, b in keep if min(b, shift + duration) > max(a, shift)]
    return merge([(to_out(a, keep), to_out(b, keep)) for a, b in inside])


def line_up(ctx) -> Dict[int, List[Span]]:
    """Offsets of every camera and of the sound by sound; a file that cannot be lined up is left out with a note.
    Returns where each camera that stays (1, 2 …) has picture, in seconds of the cut video."""
    from ..media import MediaError, probe
    from ..media.sync import offset

    cover: Dict[int, List[Span]] = {}
    cams: List = []
    for path in ctx.cameras:
        try:
            shift = offset(ctx.src, path)
        except MediaError as exc:
            ctx.note("Камера {} не использована: {}".format(path.name, exc))
            continue
        ctx.offsets[str(path)] = shift
        cams.append(path)
        cover[len(cams)] = covered(ctx.keep, shift, probe(path)["duration"])
    ctx.cameras = cams
    if ctx.audio_src is not None:
        try:
            shift = offset(ctx.src, ctx.audio_src)
            whole = covered(ctx.keep, shift, probe(ctx.audio_src)["duration"])
            if not _covers(whole, 0.0, length(ctx.keep)):
                raise MediaError("звук записан не на всё, что остаётся в ролике")
            ctx.offsets[str(ctx.audio_src)] = shift
        except MediaError as exc:
            ctx.note("Отдельный звук {} не использован, звук — с главной камеры: {}".format(ctx.audio_src.name, exc))
            ctx.audio_src = None
    return cover


def _crop_at(shot: Dict, a: float, b: float) -> Optional[Dict]:
    """The crop of the part a..b of a shot: a push-in is split so the zoom goes on smoothly across the pieces."""
    crop = shot["crop"]
    if not crop or crop.get("to") is None:
        return crop
    def zoom(t):
        return crop["zoom"] + (crop["to"] - crop["zoom"]) * (t - shot["start"]) / max(shot["end"] - shot["start"], _EPS)
    return dict(crop, zoom=round(zoom(a), 5), to=round(zoom(b), 5))


def lay_angles(ctx, keep: Sequence[Span], out):
    """The cut video made from the program: each kept piece split where the angle changes, the sound apart if given."""
    from ..media.cut import cut_program
    from .voice import clean_of

    inputs = [ctx.src] + list(ctx.cameras) + ([clean_of(ctx, ctx.audio_src)] if ctx.audio_src else [])
    shift = [0.0] + [ctx.offsets[str(c)] for c in ctx.cameras]
    sound, sound_shift = (len(inputs) - 1, ctx.offsets[str(ctx.audio_src)]) if ctx.audio_src else (0, 0.0)
    pieces, passed = [], 0.0
    for a, b in keep:
        inner = [s["start"] for s in ctx.angles if passed + 0.002 < s["start"] < passed + b - a - 0.002]
        edges = [passed] + inner + [passed + b - a]
        for x, y in zip(edges, edges[1:]):
            shot = next((s for s in ctx.angles if s["start"] - _EPS <= (x + y) / 2.0 <= s["end"] + _EPS), ctx.angles[-1])
            cam, src_a = shot["camera"], a + x - passed
            pieces.append({"input": cam, "start": max(0.0, src_a - shift[cam]), "end": src_a + y - x - shift[cam],
                           "crop": _crop_at(shot, x, y), "sound": [sound, max(0.0, src_a - sound_shift)]})
        passed += b - a
    short = [s for s in ctx.angles if s["end"] - s["start"] < SHORTEST - 0.01]
    if short:
        ctx.note("РАКУРС КОРОЧЕ {:g} С: {}. Это дефект шага".format(SHORTEST, ", ".join(
            "{:.1f}–{:.1f}".format(s["start"], s["end"]) for s in short)))
    return cut_program(inputs, pieces, out)


def plan_angles(ctx) -> None:
    cover = line_up(ctx)
    ctx.angles = program(length(ctx.keep), change_points(ctx), cameras=1 + len(ctx.cameras), cover=cover)
    side = [s for s in ctx.angles if s["camera"]]
    crop = sum(s["end"] - s["start"] for s in ctx.angles if s["crop"] and s["crop"].get("to") is None)
    ctx.report["angles"] = {"plan": ctx.angles, "offsets": dict(ctx.offsets)}
    ctx.note("Ракурсы: {} смен, кроп {:.0f} % времени, боковая камера {} раз, самый короткий ракурс {:.1f} с".format(
        len(ctx.angles) - 1, 100.0 * crop / max(length(ctx.keep), _EPS), len(side),
        min(s["end"] - s["start"] for s in ctx.angles)))
    if ctx.offsets:
        ctx.note("Сдвиг по звуку относительно главной камеры: {}".format("; ".join(
            "{} {:+.2f} с".format(Path(f).name, s) for f, s in ctx.offsets.items())))

"""The `teaser` step: a short fast walk through a long video, so it is felt as long and whole.

Black, a Play button, it is pressed, and the video runs: phrases at speaking speed between fast-forwards, a bar with
the time of the whole video over them. The draft takes phrases evenly through the video; the person, or the model
without questions, picks the moments that are worth it. It keeps the frame of the source.
"""
from __future__ import annotations

from typing import Dict, List

from .errors import PipelineError
from .words import phrases, quote, spoken

BLACK, PRESS, INTRO = 0.45, 1.05, 1.3  # s: the button comes up, is pressed, the video starts
SPEECH, FAST, FAST_SECONDS = 1.2, 6.0, 1.6  # how the draft runs phrases and fast-forwards
SLOWEST, FASTEST = 0.5, 32.0
FPS = 30


def _draft(ctx, seconds: float) -> List[Dict]:
    total = float(ctx.info["duration"])
    ph = [p for p in phrases(spoken(ctx.transcript())) if 1.5 <= p["end"] - p["start"] <= 5.0]
    room = max(1, int((seconds - INTRO) / (3.5 + FAST_SECONDS)))
    out: List[Dict] = []
    for k in range(room):
        lo, hi = total * k / room, total * (k + 1) / room
        p = next((x for x in ph if lo <= x["start"] < hi), None)
        a, b = (p["start"], p["end"] + 0.1) if p else (lo, min(hi, lo + 3.5))  # no short phrase here: a piece as it is
        item = {"start": round(a, 3), "end": round(b, 3), "rate": SPEECH}
        out.append(dict(item, said=quote(p["words"])) if p else item)
        c, d = b + 0.5, min(hi, b + 0.5 + FAST * FAST_SECONDS)
        if d - c > FAST * 0.5:
            out.append({"start": round(c, 3), "end": round(d, 3), "rate": FAST})
    return out


def rate_of_fragment(f: Dict) -> float:
    rate = float(f.get("rate", 1.0))
    if not SLOWEST <= rate <= FASTEST:
        raise PipelineError("Скорость фрагмента тизера — от {} до {}; сейчас: {}".format(SLOWEST, FASTEST, rate))
    return rate


def check_fragments(fragments: List[Dict], total: float) -> None:
    """Refused here, before anything is rendered: a fragment past the end would put the bar and the sounds off."""
    last = 0.0
    for f in fragments:
        rate_of_fragment(f)
        a, b = float(f["start"]), float(f["end"])
        if not 0 <= a < b <= total + 0.05:
            raise PipelineError("Фрагмент тизера {}–{} вне ролика длиной {:.1f} с".format(a, b, total))
        if a < last:
            raise PipelineError("Фрагменты тизера идут по порядку ролика: {} после {}".format(a, last))
        last = b


def plan_teaser(ctx) -> None:
    from ..render.design import spec
    from ..render.errors import RenderError

    try:
        spec(ctx.design(), "teaser")
    except RenderError:
        raise PipelineError("В дизайн-системе формата нет video.teaser: возьмите его из примера chrome-graphite в tokens.json.")
    seconds = float(ctx.p("teaser_seconds", 30))
    ok, data = ctx.ask("teaser", "Тизер: фрагменты по порядку, start/end по времени исходника, rate — скорость "
                       "(от 2 — быстрая перемотка). Выберите моменты, которые сами по себе цепляют. Без тизера — отказ.",
                       {"seconds": seconds, "fragments": _draft(ctx, seconds)})
    ctx.teaser = list(data.get("fragments") or []) if ok else []
    check_fragments(ctx.teaser, float(ctx.info["duration"]))


def moments(fragments: List[Dict]) -> List[Dict]:
    """For each frame of the teaser's body: where in the full video it is, and how fast it runs."""
    out: List[Dict] = []
    for f in fragments:
        a, b, rate = float(f["start"]), float(f["end"]), rate_of_fragment(f)
        out += [{"t": a + k * rate / FPS, "rate": rate} for k in range(int(round((b - a) / rate * FPS)))]
    return out


def render_teaser(ctx) -> Dict:
    from .. import media
    from ..media.teaser import montage
    from ..media.vertical import shown_size
    from ..render.player import frames_pattern, play_frames, strip_frames
    from .aftercare import fit_audio
    from .render import _clear_place, name_of

    tmp = ctx.work / "тизер"
    size = shown_size(ctx.info)
    design = ctx.design()
    play_frames(design, size, tmp / "начало", FPS, BLACK, PRESS, INTRO)
    strip = strip_frames(design, size[0], size[1], moments(ctx.teaser), float(ctx.info["duration"]), tmp / "полоса")
    cur = montage(ctx.src, ctx.teaser, frames_pattern(tmp / "начало"), INTRO, PRESS, strip, tmp / "1-сборка.mp4",
                  size=size, fps=FPS)
    if ctx.has("loudnorm"):
        cur = fit_audio(media.loudnorm(cur, tmp / "2-громкость.mp4", lufs=float(ctx.p("lufs", -16))), tmp / "3-ровно.mp4")
    final = name_of(ctx, {"name": ctx.p("teaser_name") or ctx.src.stem + "-тизер"})
    _clear_place(ctx, final, False)
    cur.replace(final)
    drift = media.drift_ms(final)
    ctx.report["drift_ms"] = max(ctx.report["drift_ms"], drift)
    return {"id": "teaser", "video": final, "duration": round(media.probe(final)["duration"], 3), "drift_ms": drift}

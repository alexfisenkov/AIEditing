"""The `publish_pack` step: `публикация.md` next to the video and frames for the covers; nothing is uploaded.

The pack holds YouTube chapters by YouTube's rules (the first at 0:00, three at least, in order, each 10 s or longer: a
chapter that breaks them merges with its neighbour), places for three titles, the description and the tags — the agent
writes those words by the method, the pipeline never does — and frames from the pauses of the speech, spread over the
video, for `run.py covers`; when the cut left fewer than six pauses, the sharpest frames of the video fill the rest.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from .chapters import out_at
from .speed import rate_of
from .timeline import to_out
from .words import spoken

FILE = "публикация.md"
FRAMES = Path("обложки") / "кадры"
WINDOWS = 12       # frames for the covers: one in each twelfth of the video
MIN_CHAPTER = 10   # seconds, YouTube's shortest chapter
MIN_PAUSE = 0.35   # a gap between words this long is a pause a face rests in
INTRO = "[название вступления — впиши]"


def clock(t: float, total: float) -> str:
    t = int(t)
    if total >= 3600:
        return "{}:{:02d}:{:02d}".format(t // 3600, t % 3600 // 60, t % 60)
    return "{}:{:02d}".format(t // 60, t % 60)


def youtube_chapters(chapters, total: float) -> List[Tuple[int, str]]:
    """[(whole second, title)] that YouTube shows as chapters, or [] when fewer than three survive the rules."""
    items = sorted((int(float(t)), str(title).strip() or INTRO) for t, title in chapters if 0 <= float(t) < total)
    if not items:
        return []
    if items[0][0] > 0:
        items = [(0, items[0][1])] + items[1:] if items[0][0] < MIN_CHAPTER else [(0, INTRO)] + items
    out: List[Tuple[int, str]] = []
    for t, title in items:
        if out and t - out[-1][0] < MIN_CHAPTER:
            if out[-1][0] == 0:
                continue  # the chapter at 0:00 stays; the one too close to it goes
            out.pop()     # the short one goes: its seconds belong to the chapter before it
        out.append((t, title))
    while len(out) > 1 and int(total) - out[-1][0] < MIN_CHAPTER:
        out.pop()
    return out if len(out) >= 3 else []


def _length(ctx) -> float:
    return sum(b - a for a, b in ctx.keep) / rate_of(ctx.p("speed", 1.0))


def _chapters(ctx) -> List[Tuple[float, str]]:
    rate = rate_of(ctx.p("speed", 1.0))
    found = [(out_at(c["start"], ctx.keep), str(c.get("title") or "")) for c in ctx.chapters or []]
    return [(t / rate, title) for t, title in found if t is not None]


def pauses(ctx) -> List[Tuple[float, float]]:
    """Gaps between the words in seconds of the finished video, the longest first."""
    rate, total = rate_of(ctx.p("speed", 1.0)), _length(ctx)
    marks = []
    for w in spoken(ctx.transcript()):
        a, b = to_out(float(w["start"]), ctx.keep), to_out(float(w["end"]), ctx.keep)
        if a is not None and b is not None:
            marks.append((a / rate, b / rate))
    edges = [0.0] + [x for m in sorted(marks) for x in m] + [total]
    gaps = [(a, b) for a, b in zip(edges[0::2], edges[1::2]) if b - a >= MIN_PAUSE]
    return sorted(gaps, key=lambda g: g[0] - g[1])


def moments(ctx) -> List[float]:
    """A moment in the longest pause of each twelfth of the video (none where nobody pauses)."""
    total, found = _length(ctx), pauses(ctx)
    step, picked = total / WINDOWS, []
    for k in range(WINDOWS):
        lo, hi = k * step, (k + 1) * step
        inside = [(max(a, lo), min(b, hi)) for a, b in found if min(b, hi) - max(a, lo) >= MIN_PAUSE]
        if inside:
            a, b = max(inside, key=lambda g: g[1] - g[0])
            picked.append(round((a + b) / 2.0, 1))
    return picked


def _frames(ctx, final: Path, total: float) -> Tuple[List[Tuple[Path, float]], List[float]]:
    """The frames for the covers and the moments of them that came from the video, not from a pause."""
    from ..media import covers

    found = moments(ctx)
    more = covers.more_moments(final, found, total) if len(found) < covers.FEW else []
    return covers.grab(final, sorted(found + more), Path(ctx.outdir) / FRAMES), more


def _whence(frames, more: List[float]) -> str:
    extra = sum(1 for _p, t in frames if t in more)
    said = "в паузах речи — {}".format(len(frames) - extra)
    return said + ("; пауз мало, ещё {} — самые резкие кадры ролика, равномерно по длине".format(extra) if extra else "")


def _chapter_lines(ctx, total: float) -> List[str]:
    raw = _chapters(ctx)
    got = youtube_chapters(raw, total)
    if not got:
        why = "в ролике нет глав (шаг глав не выбран)" if not raw else "меньше трёх глав проходят правила YouTube"
        return ["Глав для YouTube нет: {}. Без глав описание остаётся как есть.".format(why)]
    lines = ["Главы:", ""] + ["{} {}".format(clock(t, total), title) for t, title in got]
    merged = [title for _t, title in raw if title not in {g[1] for g in got}]
    if merged:
        lines += ["", "Слиты с соседними (короче 10 с): {}.".format(
            ", ".join("«{}»".format(t) for t in merged))]
    return lines


def write_pack(ctx, final: Path) -> Path:
    """`публикация.md` and `обложки/кадры/` in the issue folder; returns the file."""
    final, total = Path(final), _length(ctx)
    frames, more = _frames(ctx, final, total)
    lines = ["# Публикация: {}".format(final.stem), "",
             "Ролик: {}, длина {}. Это заготовка: ничего не загружено и не опубликовано. Слова пишет агент по "
             "методу публикации, выбирает человек.".format(final.name, clock(total, total)), "",
             "## Названия", "", "До 100 символов, главное — в первых 50.", ""]
    lines += ["{0}. [НАЗВАНИЕ {0} — впиши]".format(k) for k in (1, 2, 3)]
    lines += ["", "## Описание", "", "[ОПИСАНИЕ — впиши: первые две строки — о чём ролик и что зритель получит]", ""]
    lines += _chapter_lines(ctx, total)
    lines += ["", "## Теги", "", "[ТЕГИ — впиши через запятую]", "", "## Обложка", "",
              "Кадры-кандидаты ({}): {}. Выберите резкие, с открытыми глазами.".format(len(frames), _whence(frames, more)), ""]
    lines += ["- {} — {}.{}{}".format(p.name, clock(t, total), int(round(t * 10)) % 10, ", из ролика" if t in more else "")
              for p, t in frames]
    lines += ["", "Шесть обложек и лист: `python tools/run.py covers \"{}\" --text \"2–4 слова\"`; ещё шесть — тем же "
              "с `--more`.".format(Path(ctx.outdir))]
    path = Path(ctx.outdir) / FILE
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(path))
    return path


def plan_publish(ctx) -> None:
    """Hears the speech while planning, so a recogniser that fails stops the run before the render, not after it."""
    ctx.transcript()


def pack_files(ctx, final: Path) -> Dict:
    path = write_pack(ctx, final)
    return {"publish": path, "frames": len(list((Path(ctx.outdir) / FRAMES).glob("кадр-*.jpg")))}

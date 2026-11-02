"""`отчёт.md` next to the video: what was cut, closed, fixed, how in sync, and notes for refinement."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .speed import rate_of, scale_rows
from .timeline import to_out

NAME = "отчёт.md"
DRIFT_OK = 40.0


def stamp(t: float) -> str:
    t = max(0.0, float(t))
    return "{:d}:{:02d}:{:04.1f}".format(int(t // 3600), int(t // 60 % 60), t % 60)


def _list(rows: List[str]) -> List[str]:
    return rows or ["- —"]


def _uncut(ctx) -> bool:
    keep = ctx.keep
    return (not ctx.pieces and len(keep) == 1 and keep[0][0] <= 0.05 and keep[0][1] >= ctx.info["duration"] - 0.05)


def _from_recording(ctx, drift: float) -> bool:
    """Nothing was cut and the recording itself measures the same: the difference came with it."""
    if drift < DRIFT_OK or not _uncut(ctx):
        return False
    from ..media import drift_ms

    return abs(drift_ms(ctx.src) - drift) < DRIFT_OK


def _body(ctx, r: Dict) -> List[str]:
    lines = ["# Отчёт монтажа", "", "Исходник: {}".format(ctx.src.name),
             "Формат: {}; шаги: {}".format(ctx.profile.get("format", ""), ", ".join(ctx.steps)), "",
             "## Готовое", ""]
    for o in r["outputs"]:
        lines.append("- {} — {} с{}".format(Path(o["video"]).name, o["duration"],
                                             ", субтитры " + Path(o["srt"]).name if o.get("srt") else ""))
        lines += ["  - {}".format(Path(e).name) for e in o.get("exports", [])]
    lines += ["", "## Вырезано", ""] + _list(["- {}–{}: {}".format(stamp(c["start"]), stamp(c["end"]), c["why"])
                                               for c in r["cuts"]])
    lines += ["", "## Закрыто блюром", ""] + _list(["- {}–{}: {}".format(stamp(b["start"]), stamp(b["end"]),
                                                                       b.get("what", "область")) for b in r["blurred"]])
    lines += ["", "## Исправления в субтитрах", ""] + _list(["- №{} ({}): «{}» → «{}»".format(
        f["index"], stamp(f["start"]), f["from"], f["to"]) for f in r["fixes"]])
    if r["chapters"]:
        lines += ["", "## Главы", ""] + ["- {} {}".format(stamp(c["at"]), c["title"]) for c in r["chapters"]]
    if r.get("animations"):
        lines += ["", "## Анимации", ""] + ["- {}–{} «{}»: {}".format(
            stamp(a["at"]), stamp(a["end"]), a["template"], " · ".join(x for x in (a["title"], a["text"]) if x))
            for a in r["animations"]]
    if r["clips"]:
        lines += ["", "## Отрывки", ""] + ["- {} {}–{}: {}".format(c["id"], stamp(c["start"]), stamp(c["end"]),
                                                                 c.get("said", "")) for c in r["clips"]]
    sync = "в норме" if r["drift_ms"] < DRIFT_OK else ("так в самой записи, склеек нет" if r.get("drift_in_source") else
                                                       "БОЛЬШЕ НОРМЫ ({:.0f} мс)".format(DRIFT_OK))
    lines += ["", "## Синхрон", "", "- рассинхрон звука и картинки: {:.1f} мс — {}".format(r["drift_ms"], sync)]
    if "words_lost" in r and any(ctx.has(s) for s in ("verify_words",)):
        lost = ", ".join("«{}» ({})".format(w["text"], stamp(w["at"])) for w in r["words_lost"])
        lines.append("- повторная расшифровка: {}".format("ни одно слово не потеряно" if not lost else
                                                         "не слышно: " + lost))
    if getattr(ctx.approve, "auto", False):
        lines += ["", "## Решено без вопросов", ""] + _list(["- {}: {}".format(
            d["key"], "принято" if d["ok"] else "отказ") for d in ctx.decisions])
    lines += ["", "## Замечания для доработки", ""] + _list(["- " + n for n in ctx.notes])
    return lines


def finish(ctx) -> Dict:
    r = ctx.report
    rate = rate_of(ctx.p("speed", 1.0))
    r["chapters"] = [{"at": (to_out(float(c["start"]), ctx.keep) or 0.0) / rate, "title": c["title"]}
                     for c in ctx.chapters]
    r["blurred"] = scale_rows(r["blurred"], rate, "start", "end")
    if r.get("animations"):
        r["animations"] = scale_rows(r["animations"], rate, "at", "end")
    if rate != 1.0:
        ctx.note("Готовое видео ускорено в {:g} раза: таймкоды глав и субтитров — уже с ускорением, "
                 "вырезанное указано по времени исходника".format(rate))
    r["clips"] = [{k: p[k] for k in ("id", "start", "end", "said") if k in p} for p in (ctx.pieces or [])]
    r["drift_in_source"] = _from_recording(ctx, r["drift_ms"])
    if r["drift_ms"] >= DRIFT_OK and not r["drift_in_source"]:
        ctx.note("Рассинхрон {:.0f} мс — больше {:.0f} мс; проверьте склейки".format(r["drift_ms"], DRIFT_OK))
    if r["words_lost"]:
        ctx.note("Повторная расшифровка не слышит {} слов — проверьте места склеек".format(len(r["words_lost"])))
    first = r["outputs"][0] if r["outputs"] else {}
    r.update(output=first.get("video"), srt=first.get("srt"), notes=list(ctx.notes), decisions=ctx.decisions)
    path = ctx.outdir / NAME
    path.write_text("\n".join(_body(ctx, r)) + "\n", encoding="utf-8")
    r["report"] = path
    return r

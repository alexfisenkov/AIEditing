"""The `timeline` step: next to the video, `<name>.fcpxml` for DaVinci Resolve and `таймлиния.md`, how to open it.

params.timeline = true | {"layers": "layers" | "picture"}. "layers" (the default): the camera in the pieces the cut kept
(its sound is the voice), the inserts, the plates and inserts of the design layer (copied to `таймлиния/`, the run folder
goes), the music and its variants on lanes of their own, switched off; markers of chapters, inserts and edits. Times are
those of the cut before `params.speed`. "picture": the finished video in one clip with the same markers. A format with
the graphics kit gets its timeline from `overlay.py timeline` once the graphics are laid. Nothing is uploaded.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Optional

from ..media import fcpxml
from .speed import rate_of
from .timeline import to_out

NOTE = "таймлиния.md"
FOLDER = "таймлиния"
VARIANTS = "музыка-варианты"
QUIET_CUTS = ("пауза", "звук без слов")  # not worth a marker: there are hundreds of them


def mode(ctx) -> str:
    raw = ctx.p("timeline")
    chosen = raw.get("layers", "layers") if isinstance(raw, dict) else "layers"
    return chosen if chosen in ("layers", "picture") else "layers"


def plan_timeline(ctx) -> None:
    if ctx.has("graphics"):
        ctx.note("Таймлиния формата с графикой делается после неё: overlay.py timeline <рабочая папка> <папка выпуска>")


def _seam(t: float, keep) -> float:
    return sum(min(b, t) - a for a, b in keep if a < t)


def _camera(ctx, keep) -> List[Dict]:
    clips, at = [], 0.0
    for a, b in keep:
        clips.append({"file": str(ctx.src), "start": at, "in": a, "dur": b - a})
        at += b - a
    return clips


def _inserts(ctx, keep) -> List[Dict]:
    out = []
    for b in ctx.broll or []:
        at = to_out(float(b["start"]), keep)
        if at is not None:
            out.append({"file": b["file"], "start": at, "in": 0.0 if b.get("kind") == "photo" else float(b.get("from") or 0),
                        "dur": float(b["end"]) - float(b["start"]), "muted": True})
    return out


def _pictures(ctx, pictures) -> List[Dict]:
    """The design layer's PNG and clips, copied next to the video: the run folder that held them is removed."""
    folder, out = Path(ctx.outdir) / FOLDER, []
    for k, p in enumerate(sorted(pictures or [], key=lambda p: float(p["start"]))):
        src = Path(p.get("png") or p.get("video"))
        if not src.is_file():
            continue
        folder.mkdir(parents=True, exist_ok=True)
        copy = folder / "{}-{:02d}{}".format("плашка" if p.get("png") else "анимация", k + 1, src.suffix)
        shutil.copyfile(str(src), str(copy))
        out.append({"file": str(copy), "start": float(p["start"]), "in": 0.0,
                    "dur": float(p["end"]) - float(p["start"]), "muted": True})
    return out


def _music(ctx, total: float) -> List[Dict]:
    from ..media import probe

    music = ctx.music or {}
    if not ctx.has("music") or not (music.get("track") or music.get("tracks")):
        return []
    beds = [Path(ctx.outdir) / VARIANTS / "вариант-{}.m4a".format(k + 1) for k in range(int(music.get("variants") or 1))]
    beds = [b for b in beds if b.is_file()] if music.get("tracks") else []
    if beds:  # already levelled under the voice: the first plays, the others wait switched off
        return [{"name": "Музыка" if k == 0 else "Музыка, вариант {}".format(k + 1), "role": "music",
                 "clips": [{"file": str(b), "start": 0.0, "in": 0.0, "dur": min(total, probe(b)["duration"]), "off": k > 0}]}
                for k, b in enumerate(beds)]
    track, clips, at = Path(music["track"]), [], 0.0
    length = probe(track)["duration"]
    while at < total - 0.05 and length > 0.5:
        clips.append({"file": str(track), "start": at, "in": 0.0, "dur": min(length, total - at), "db": music.get("db", -20)})
        at += length
    return [{"name": "Музыка", "role": "music", "clips": clips}] if clips else []


def _markers(ctx, keep, scale: float) -> List[Dict]:
    out = []
    for c in ctx.chapters or []:
        at = to_out(float(c["start"]), keep)
        if at is not None and str(c.get("title") or "").strip():
            out.append({"t": at / scale, "text": str(c["title"]).strip(), "kind": "chapter"})
    for b in ctx.broll or []:
        at = to_out(float(b["start"]), keep)
        if at is not None:
            out.append({"t": at / scale, "text": "вставка: {}".format(b.get("phrase") or Path(b["file"]).name), "kind": "broll"})
    for c in (ctx.report or {}).get("cuts") or []:
        if not str(c.get("why", "")).startswith(QUIET_CUTS):
            out.append({"t": _seam(float(c["start"]), keep) / scale, "text": "правка: {}".format(c["why"]), "kind": "edit"})
    return out


def write_timeline(ctx, final: Path, pictures: Optional[List[Dict]] = None) -> Path:
    """`<final stem>.fcpxml` and `таймлиния.md` in the issue folder; returns the timeline."""
    from ..media import probe
    from ..media.vertical import shown_size

    final, keep = Path(final), ctx.keep
    info = probe(final)
    width, height = shown_size(info)
    spec = {"name": final.stem, "fps": info["fps"] or 25.0, "width": width, "height": height, "audio": []}
    if mode(ctx) == "picture":
        spec.update(duration=info["duration"], markers=_markers(ctx, keep, rate_of(ctx.p("speed", 1.0))),
                    video=[{"name": "Готовый ролик", "clips": [{"file": str(final), "start": 0.0, "in": 0.0,
                                                                "dur": info["duration"]}]}])
    else:
        total = sum(b - a for a, b in keep)
        spec.update(duration=total, markers=_markers(ctx, keep, 1.0), audio=_music(ctx, total),
                    video=[{"name": "Камера", "clips": _camera(ctx, keep)},
                           {"name": "Вставки", "clips": _inserts(ctx, keep)},
                           {"name": "Плашки", "clips": _pictures(ctx, pictures)}])
        spec["video"] = spec["video"][:1] + [lane for lane in spec["video"][1:] if lane["clips"]]
    path = fcpxml.write(spec, Path(ctx.outdir) / (final.stem + ".fcpxml"))
    fcpxml.write_note(spec, path, Path(ctx.outdir) / NOTE, final.name, _extra(ctx, spec))
    return path


def _extra(ctx, spec: Dict) -> List[str]:
    lines = []
    if spec["video"][0]["name"] == "Камера":
        lines.append("Голос — это звук клипов «Камера»: отдельной дорожки голоса нет.")
        rate = rate_of(ctx.p("speed", 1.0))
        if rate != 1.0:
            lines.append("Готовый ролик ускорен в {:g} раза, а на таймлинии время до ускорения. Чтобы совпало: выделите "
                         "все клипы и поставьте скорость {:g} %.".format(rate, rate * 100))
    if any(lane["name"] == "Плашки" for lane in spec["video"]):
        lines.append("Плашки лежат картинками в папке «{}» рядом с роликом.".format(FOLDER))
    return lines

"""Frames and layout of the person's sources, design variants on their frames — all onto the dashboard."""
from __future__ import annotations

import shutil
from pathlib import Path

import state as st

from . import session
from .profiles import _value
from .session import CliError
from .trial import Waiting, cmd_trial, cmd_verdict  # noqa: F401  (re-exported for the parser)


def _source(data: dict, sid: str) -> dict:
    found = next((s for s in data.get("sources", []) if s["id"] == sid), None)
    if not found:
        raise CliError("Исходника {} нет; есть: {}".format(sid, ", ".join(s["id"] for s in data["sources"]) or "—"))
    return found


def _keep(files, folder: Path):
    """Files land in `folder` under their own names: a frame's time lives in its name (look.frame_time)."""
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for f in map(Path, files):
        dst = folder / f.name
        if f.resolve() != dst.resolve():
            shutil.copy2(str(f), str(dst))
        out.append(dst)
    return out


def cmd_frames(opt) -> str:
    from runtime import look

    src = Path(opt.video).expanduser().resolve()
    if not src.is_file():
        raise CliError("Нет такого файла: {}".format(src))
    data, w = session.load(), session.work()
    sid = "s{}".format(len(data.get("sources", [])) + 1)
    folder = w / "sources" / sid
    shots = _keep(look.frames(src, opt.n, outdir=folder), folder)
    row = {"id": sid, "name": src.name, "frames": [st.rel(w, p) for p in shots], "layout": None}
    data.setdefault("sources", []).append(row)
    st.log(data, "frames", source=sid, note="{} — {} кадров".format(src.name, len(shots)))
    session.commit(data)
    return "{}: {} кадров из {} — на дашборде".format(sid, len(shots), src.name)


def cmd_layout(opt) -> str:
    data, w = session.load(), session.work()
    src = _source(data, opt.source)
    if opt.set:
        layout = dict(src.get("layout") or {}, by="person", confidence=1.0)  # what is not corrected stays
        for item in opt.set:
            key, _, raw = item.partition("=")
            layout[key.strip()] = _value(raw.strip())
    else:
        from runtime import look

        frames = [w / f for f in src["frames"]]
        if opt.with_source:  # two recordings of one session: separate tracks
            frames = [frames, [w / f for f in _source(data, opt.with_source)["frames"]]]
        layout = dict(look.detect_layout(frames), by="auto")
    src["layout"] = layout
    st.log(data, "layout", source=src["id"], note=str(layout.get("kind")))
    session.commit(data)
    return "{}: раскладка {} ({})".format(src["id"], layout.get("kind"), layout["by"])


def cmd_samples(opt) -> str:
    from runtime import render

    data, w = session.load(), session.work()
    frame, face = (Path(opt.frame).resolve(), None) if opt.frame else _first_frame(data, w)
    own = w / opt.skill / "design"
    design = own if (own / "tokens.json").is_file() else None  # None: the bundled example
    folder = w / opt.skill / "variants" / opt.element
    shots = _keep(render.samples(design, frame, kind=opt.element, face=face, outdir=folder), folder)
    row = {"skill": opt.skill, "element": opt.element, "files": [st.rel(w, p) for p in shots], "at": st.now()}
    data["design"]["samples"] = [s for s in data["design"]["samples"]
                                 if (s["skill"], s["element"]) != (opt.skill, opt.element)] + [row]
    st.log(data, "samples", skill=opt.skill, note="{}: {} вариантов".format(opt.element, len(shots)))
    session.commit(data)
    example = "" if design else " (на примере Chrome & Graphite: своего design/tokens.json ещё нет)"
    return "{} вариантов «{}» — на дашборде рядом{}".format(len(shots), opt.element, example)


def _first_frame(data: dict, w: Path):
    for s in data.get("sources", []):
        if s.get("frames"):
            return w / s["frames"][0], (s.get("layout") or {}).get("face")
    raise CliError("Нет кадров исходника: сначала ae.py frames <видео> или --frame")

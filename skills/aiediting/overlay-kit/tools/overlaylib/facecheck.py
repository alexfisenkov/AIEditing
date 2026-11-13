"""The face check of a render: right after every change of the picture the speaker's face is whole inside the speaker's window.

The frames are rendered from the composition itself (tools/face-frames.mjs), and the presenter tells where its window is on
each of them (src/kit/speakerBox.ts). A frame where the window shows no face, or cuts the face, is a finding. The frames
looked at: MOMENTS after every cut of the face track and every joint of an edit by markers across which the face jumps; in a
vertical clip also after every joint of two spans.

Every check returns (findings, unchecked): `unchecked` is the reason nothing could be judged. It is never a pass: `draft`
fails on it, `final` and `vertical-final` stop on it unless the person accepts it with a reason.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import face, facecmd, facejudge, remotion, vmap, vsheets, vspans
from .common import FPS, KIT, ToolError, run, say

MOMENTS = (0.2, 1.0)  # seconds after a change at which the frame is looked at
HELPER = "face-frames.mjs"
LONG = "Full"
NO_BOX = "РАМКА СПИКЕРА НЕ СООБЩЕНА"
NO_TRACK = "трека лица нет, рамка стоит по центру"  # a video with no face to follow: `draft` warns, only a release stops on it
Outcome = Tuple[List[str], Optional[str]]


def long_frames(track: Sequence, rows: Sequence, total: int) -> List[int]:
    """Frames of the long video to look at; `total` is its length in frames."""
    found = {int(round((second + m) * FPS)) for second in facecmd.cut_seconds(track, rows) for m in MOMENTS}
    return sorted(f for f in found if 0 <= f < total)


def span_edges(spans: Sequence[Sequence[float]], rate: float) -> List[int]:
    """The first frame of every span and the end of the speech: spanEdges of template/src/vertical/spanTime.ts."""
    total, edges = 0.0, [0]
    for a, b in spans:
        total += (b - a) / rate
        edges.append(vspans.js_round(total * FPS))
    return edges


def clip_frames(track: Sequence, rows: Sequence, data: Dict, cid: str) -> List[int]:
    """Frames of a vertical clip to look at: after every joint of two spans and every change of the picture inside a span."""
    spans, rate = data["spans"][cid], data["rate"]
    edges = span_edges(spans, rate)
    starts = set(edges[1:-1])
    for second in facecmd.cut_seconds(track, rows):  # seconds of the file, like the spans
        for k, (a, b) in enumerate(spans):
            if a <= second < b:
                starts.add(edges[k] + vspans.js_round((second - a) / rate * FPS))
    found = {start + int(round(m * FPS)) for start in starts for m in MOMENTS}
    return sorted(f for f in found if f < edges[-1])


def why_not(work: Path, reader: str) -> Optional[str]:
    """The reason a folder cannot be checked, or None. `reader`: the presenter the composition uses."""
    reason = facejudge.ready()
    if reason:
        return reason + " (их ставит ae.py setup)"
    if reader in facecmd.stale_readers(work):
        return "{} прежнего образца, рамку спикера не сообщает: обновите его ({})".format(reader, facecmd.FIX[reader])
    track = face.load(work)
    if track == [face.CENTRE]:
        return NO_TRACK + ": в видео не нашлось лица, или трек не строили. Если лицо в кадре есть: overlay.py face <папка> --rebuild"
    if face.is_old_kind(track):
        return "трек лица прежнего образца не знает смен картинки. Пересобрать: overlay.py face <папка> --rebuild" + (
            " --video <первый принятый ролик>" if vmap.load_rows(work) else "")
    return None


def render(work: Path, site: Path, composition: str, frames: Sequence[int], props: Dict, out: Path) -> None:
    """Into a folder of this run only: two checks at once never take each other's frames."""
    dst = work / "tools-local"
    dst.mkdir(exist_ok=True)
    shutil.copyfile(str(KIT / "tools" / HELPER), str(dst / HELPER))  # inside the folder, to see its node_modules
    run(["node", "tools-local/" + HELPER, str(site), str(out), composition, ",".join(map(str, frames)), json.dumps(props)],
        "Кадры для проверки лица (" + composition + ")", cwd=work)


def judge_folder(out: Path, detector) -> Tuple[List[str], int]:
    """(findings, frames judged). A frame without a window that is not hidden is a finding too: it was not checked."""
    meta = json.loads((out / "boxes.json").read_text(encoding="utf-8"))
    files = {vsheets.frame_of(p.name): p for p in out.iterdir() if vsheets.FRAME_FILE.match(p.name)}
    found, judged = [], 0
    for frame in meta["frames"]:
        if frame not in files:
            raise ToolError("Кадр {} не отрисован: проверка неполная.".format(frame))
        box = meta["boxes"].get(str(frame))
        where = "{:.2f} с ({})".format(frame / meta["fps"], files[frame].name)
        if box is None:
            found.append("{}: {}".format(where, NO_BOX))
            continue
        if not facejudge.judgeable(box):
            continue  # hidden or too small: the speaker is not on the screen there
        judged += 1
        verdict = facejudge.judge(detector.faces(files[frame], box), box)
        if verdict:
            found.append("{}: {}".format(where, verdict))
    return found, judged


def _publish(run_dir: Path, final: Path) -> Path:
    """The frames of this run become the folder to look at; the previous run's frames go. Another check publishing at the same
    moment may win the place: then this run's frames stay where they were rendered, and that folder is named."""
    try:
        if final.is_dir():
            shutil.rmtree(str(final))
        run_dir.rename(final)
        return final
    except OSError:
        return run_dir


def _check(work: Path, site: Path, composition: str, frames: Sequence[int], props: Dict, final: Path, detector) -> List[str]:
    final.parent.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=str(final.parent)))
    keep = False  # the frames of this run stay in run_dir only when another check took the place to look at
    try:
        render(work, site, composition, frames, props, run_dir)
        found, judged = judge_folder(run_dir, detector)
        shown = _publish(run_dir, final)
        keep = shown == run_dir
    finally:
        if not keep and run_dir.is_dir():
            shutil.rmtree(str(run_dir), ignore_errors=True)
    say("{}: лицо в рамке — кадров {}, оценено {}, находок {}; кадры в {}".format(composition, len(frames), judged, len(found), shown))
    for text in found:
        say("  " + text)
    return found


def check_long(work: Path) -> Outcome:
    """The long video."""
    reason = why_not(work, "src/kit/Presenter.tsx")
    if reason:
        return [], reason
    frames = long_frames(face.load(work), vmap.load_rows(work), int(round(remotion.duration(work) * FPS)))
    if not frames:
        say("Лицо в рамке: смен картинки в треке нет, смотреть нечего.")
        return [], None
    detector, missing = facejudge.detector()
    if detector is None:
        return [], missing
    from . import vcheck  # vcheck runs the clips' check from here: imported late, the two modules lean on each other

    site = vcheck.bundle(work, "src/index.ts")
    try:
        found = _check(work, site, LONG, frames, {}, work / "out" / "face-check" / LONG, detector)
    finally:
        shutil.rmtree(str(site.parent), ignore_errors=True)
    return found, None


def check_clip(work: Path, site: Path, data: Dict, cid: str, tool) -> Outcome:
    """One vertical clip, rendered from a bundle the caller made; `tool` is what facejudge.detector() gave."""
    detector, missing = tool
    reason = why_not(work, "src/vertical/VPresenter.tsx") or (None if detector is not None else missing or "детектора лица нет")
    if reason:
        return [], reason
    frames = clip_frames(face.load(work), vmap.load_rows(work), data, cid)
    if not frames:
        return [], None
    final = work / "out" / "vertical" / cid / "face-check"
    return _check(work, site, cid, frames, {"id": cid, "audit": False}, final, detector), None


def accepted_reason(given: Optional[str]) -> Optional[str]:
    """--face-accepted needs words; an empty or blank one is refused, as --hum-accepted is."""
    if given is None:
        return None
    reason = given.strip()
    if not reason:
        raise ToolError("--face-accepted требует основание словами: что вы увидели на кадрах и решили (например «спикер отвернулся, кадры просмотрены»).")
    return reason


def gate(found: List[str], unchecked: Optional[str], accepted: Optional[str], what: str) -> None:
    """Before a release: a finding or an unchecked render stops it unless the person accepted it with a reason."""
    if not found and not unchecked:
        return
    problem = "{} находок лица в рамке".format(len(found)) if found else "лицо в рамке не проверено: {}".format(unchecked)
    if not accepted:
        raise ToolError("{}: {}. Исправьте раскладку, трек или набор (overlay.py face <папка>). Если кадры просмотрены и всё верно "
                        "(или проверить нечем, а вы смотрели глазами): --face-accepted \"основание\".".format(what, problem))
    say("{}: {} — принято человеком: «{}». Назовите это в отчёте.".format(what, problem, accepted))

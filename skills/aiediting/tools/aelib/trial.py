"""The one trial edit AIEditing makes: a piece of the person's source through `pipelines.run`, to show."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import state as st

from . import session
from .paths import FORMAT_TEMPLATE
from .session import CliError

if str(FORMAT_TEMPLATE) not in sys.path:
    sys.path.insert(0, str(FORMAT_TEMPLATE))
from approvals import FileApprover, NeedsApproval  # noqa: E402


class Waiting(Exception):
    """The trial needs the person's decision (exit code 3); the question is on the dashboard."""


def _folder(root: Path, resume: bool) -> Path:
    done = sorted(p for p in root.glob("[0-9][0-9]") if p.is_dir())
    if resume and done:
        return done[-1]
    return root / "{:02d}".format(len(done) + 1)


def _piece(src: Path, folder: Path, start, duration) -> Path:
    if start is None and duration is None:
        return src
    from runtime import media

    a = float(start or 0.0)
    b = a + float(duration) if duration else media.probe(src)["duration"]
    return media.cut_spans(src, [(a, b)], folder / ("кусок" + (src.suffix or ".mp4")))


def cmd_trial(opt) -> str:
    from runtime import pipelines
    from runtime.profile import load_profile

    w = session.work()
    try:
        profile = load_profile(w / opt.skill / "profile.json")
    except (OSError, ValueError) as e:
        raise CliError(str(e))
    src = Path(opt.video).expanduser().resolve()
    if not src.is_file():
        raise CliError("Нет такого файла: {}".format(src))
    folder = _folder(w / opt.skill / "trials", resume=bool(opt.answers))
    folder.mkdir(parents=True, exist_ok=True)
    piece = _piece(src, folder, opt.start, opt.duration)
    try:
        report = pipelines.run(piece, profile, folder / "out", FileApprover(folder, opt.answers))
    except NeedsApproval as e:
        session.event(lambda d: st.ask(d, "approve", "пробный монтаж {}: нужно решение".format(opt.skill)))
        raise Waiting("{}\nПапка пробы: {}".format(e, folder))
    video = Path((report or {}).get("output") or "")
    if not video.is_file():
        raise CliError("Конвейер не вернул готовый ролик (report['output'])")
    if w.resolve() not in video.resolve().parents:
        video = Path(shutil.copy2(str(video), str(folder / video.name)))
    row = {"skill": opt.skill, "n": folder.name, "video": st.rel(w, video), "at": st.now(), "verdict": None}

    def change(d):
        d["trials"] = [t for t in d.get("trials", []) if (t["skill"], t["n"]) != (opt.skill, folder.name)] + [row]
        st.ask(d, "trial", "так нравится? — проба {} {}".format(opt.skill, folder.name))

    session.event(change)
    return "Проба готова: {} — на дашборде; спросите «так нравится?»".format(video)


def cmd_verdict(opt) -> str:
    def change(d):
        mine = [t for t in d.get("trials", []) if t["skill"] == opt.skill]
        if not mine:
            raise CliError("Проб {} ещё не было".format(opt.skill))
        mine[-1]["verdict"] = opt.verdict
        st.close_wait(d, opt.note)
        st.log(d, "verdict", skill=opt.skill, note=opt.verdict)

    return session.event(change)

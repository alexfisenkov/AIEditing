"""The one trial edit AIEditing makes: a piece of the person's source through `pipelines.run`, to show."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import state as st

from . import session, variants
from .paths import FORMAT_TEMPLATE
from .session import CliError

if str(FORMAT_TEMPLATE) not in sys.path:
    sys.path.insert(0, str(FORMAT_TEMPLATE))
from approvals import NeedsApproval, approver_for  # noqa: E402

KEPT = ".расшифровка"  # the pipeline's folder of recognised speech (pipelines.words.KEPT)
PATH_MARK = ".путь"  # in a trial's folder: the path it probes


class Waiting(Exception):
    """The trial needs the person's decision (exit code 3); the question is on the dashboard."""


def _path_of(folder: Path) -> str:
    mark = folder / PATH_MARK
    return mark.read_text(encoding="utf-8").strip() if mark.is_file() else ""


def _folder(root: Path, resume: bool, variant=None) -> Path:
    """A run with answers goes on in the last trial, when that trial is of the same path: one answer file serves every probe."""
    done = sorted(p for p in root.glob("[0-9][0-9]") if p.is_dir())
    if resume and done and _path_of(done[-1]) == (variant or ""):
        return done[-1]
    return root / "{:02d}".format(len(done) + 1)


def _piece(src: Path, folder: Path, start, duration, name: str = "кусок") -> Path:
    if start is None and duration is None:
        return src
    from runtime import media

    a = float(start or 0.0)
    b = a + float(duration) if duration else media.probe(src)["duration"]
    suffix = src.suffix or ".mp4"
    if not media.probe(src)["has_video"]:  # a cut is AAC: a .wav of the recorder becomes .m4a
        suffix = ".m4a"
    return media.cut_spans(src, [(a, b)], folder / (name + suffix))


def _file(raw, what: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise CliError("Нет такого файла {}: {}".format(what, path))
    return path


def _screen(opt, folder: Path):
    """The screen recording of separate tracks, cut to the same piece as the camera."""
    if not getattr(opt, "screen", None):
        return None
    return _piece(_file(opt.screen, "экрана"), folder, opt.start, opt.duration, "экран")


def _others(opt) -> dict:
    """Other cameras and the sound recorded apart (step `angles`), checked before the trial makes its folder."""
    found = {}
    if getattr(opt, "camera", None):
        found["cameras"] = [_file(c, "камеры") for c in opt.camera]
    if getattr(opt, "audio", None):
        found["audio"] = _file(opt.audio, "звука")
    return found


def _cut_others(others: dict, opt, folder: Path) -> dict:
    """Each cut to the same seconds as the main camera: they started at about the same time, so `media.sync` lines the
    pieces up as it lines up the whole files."""
    out = dict(others)
    if "cameras" in out:
        out["cameras"] = [_piece(c, folder, opt.start, opt.duration, "камера-{}".format(k)) for k, c in enumerate(out["cameras"], 2)]
    if "audio" in out:
        out["audio"] = _piece(out["audio"], folder, opt.start, opt.duration, "звук")
    return out


def _own_design(profile: dict, draft: Path) -> dict:
    """A relative `design` is the draft's own folder (`<draft>/design/`), not a place inside AIEditing."""
    own = profile.get("design")
    if not own or Path(own).is_absolute():
        return profile
    return dict(profile, design=str((draft / own).resolve()))


def _probe_of(profile: dict, wanted) -> dict:
    """The row of the path this trial tries; {} for a trial of the draft as it stands, once a path is chosen."""
    if wanted:
        return variants.by_id(profile, wanted)
    no_path = variants.unchosen(profile)
    if no_path:
        raise CliError(no_path)
    return {}


def _speech_heard_before(root: Path, folder: Path) -> None:
    """The recognised speech of this very file, from the earlier trials of this format: a probe of another path does
    not hear a long recording again. The name of each file holds the recording and the recogniser."""
    target = folder / "out" / KEPT
    for kept in sorted(root.glob("[0-9][0-9]/out/" + KEPT)):
        for path in kept.glob("words-*.json"):
            if not (target / path.name).exists():
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(path), str(target / path.name))


def _on_dashboard(skill: str, folder: Path, video: Path, probe: dict) -> str:
    """The clip into the row of its trial. A probe of a path stands beside the others and asks nothing by itself."""
    w = session.work()
    if w.resolve() not in video.resolve().parents:
        video = Path(shutil.copy2(str(video), str(folder / video.name)))
    row = {"skill": skill, "n": folder.name, "video": st.rel(w, video), "at": st.now(), "verdict": None}
    if probe:
        row.update(variant=probe["id"], title=probe["title"], probe=True)

    def change(d):
        here = (skill, folder.name, row.get("variant"))
        d["trials"] = [t for t in d.get("trials", []) if (t["skill"], t["n"], t.get("variant")) != here] + [row]
        if not probe:
            st.ask(d, "trial", "так нравится? — проба {} {}".format(skill, folder.name))

    session.event(change)
    if probe:
        return "Проба пути «{}»: {} — на дашборде рядом с другими; когда покажете все, спросите, какой берём".format(probe["title"], video)
    return "Проба готова: {} — на дашборде; спросите «так нравится?»".format(video)


def cmd_trial(opt) -> str:
    from runtime import pipelines
    from runtime.profile import load_profile

    w = session.work()
    try:
        profile = load_profile(w / opt.skill / "profile.json")
    except (OSError, ValueError) as e:
        raise CliError(str(e))
    probe = _probe_of(profile, getattr(opt, "variant", None))
    if probe:
        profile = variants.switched(profile, probe, short=True)
    if "reedit" in profile["steps"] and (opt.start is not None or opt.duration is not None):
        raise CliError("Перемонтаж пробуется на всём исходнике: секунды отрывков, слов и чистой речи относятся к нему, а не к куску. "
                       "Уберите --start и --duration: короткая проба — это один отрывок в ответе clips.")
    profile = _own_design(profile, w / opt.skill)
    src = Path(opt.video).expanduser().resolve()
    if not src.is_file():
        raise CliError("Нет такого файла: {}".format(src))
    others = _others(opt)
    folder = _folder(w / opt.skill / "trials", resume=bool(opt.answers), variant=probe.get("id"))
    folder.mkdir(parents=True, exist_ok=True)
    if probe:
        (folder / PATH_MARK).write_text(probe["id"], encoding="utf-8")
    _speech_heard_before(w / opt.skill / "trials", folder)
    piece, screen = _piece(src, folder, opt.start, opt.duration), _screen(opt, folder)
    extra = dict(_cut_others(others, opt, folder), **({"screen": screen} if screen else {}))
    try:
        report = pipelines.run(piece, profile, folder / "out", approver_for(profile, folder, opt.answers), **extra)
    except NeedsApproval as e:
        session.event(lambda d: st.ask(d, "approve", "пробный монтаж {}: нужно решение".format(opt.skill)))
        raise Waiting("{}\nПапка пробы: {}".format(e, folder))
    video = Path((report or {}).get("output") or "")
    if not video.is_file():
        if (report or {}).get("handover"):  # the model makes this clip by the kit, then `ae.py show`
            return "{}\nПапка пробы: {}\nГотовый ролик на дашборд: ae.py show {} <файл>{}".format(
                report["handover"], folder / "out", opt.skill, " --variant " + probe["id"] if probe else "")
        raise CliError("Конвейер не вернул готовый ролик (report['output'])")
    return _on_dashboard(opt.skill, folder, video, probe)


def cmd_show(opt) -> str:
    """A clip the model made on top of the pipeline's work (the kit's re-edit or graphics), in the row of the last trial."""
    from runtime.profile import load_profile

    w = session.work()
    video = Path(opt.video).expanduser().resolve()
    if not video.is_file():
        raise CliError("Нет такого файла: {}".format(video))
    done = [p for p in sorted((w / opt.skill / "trials").glob("[0-9][0-9]")) if p.is_dir() and _path_of(p) == (opt.variant or "")]
    if not done:
        raise CliError("Проб {} {}ещё не было".format(opt.skill, "по пути {} ".format(opt.variant) if opt.variant else ""))
    profile = load_profile(w / opt.skill / "profile.json")
    return _on_dashboard(opt.skill, done[-1], video, variants.by_id(profile, opt.variant) if opt.variant else {})


def cmd_hear(opt) -> str:
    """What the draft's recogniser hears in a finished clip: how a path without `verify_words` checks its seams."""
    from runtime import asr
    from runtime.profile import load_profile

    profile = load_profile(session.work() / opt.skill / "profile.json")
    cfg = dict(profile["asr"], language=profile["asr"].get("language") or profile.get("language") or "")
    words = asr.transcribe(Path(opt.video).expanduser().resolve(), cfg).get("words", [])
    return "\n".join("{:7.2f} {}".format(w["start"], str(w["text"]).strip()) for w in words if str(w.get("text", "")).strip())


def cmd_verdict(opt) -> str:
    def change(d):
        mine = [t for t in d.get("trials", []) if t["skill"] == opt.skill]
        if not mine:
            raise CliError("Проб {} ещё не было".format(opt.skill))
        mine[-1]["verdict"] = opt.verdict
        st.close_wait(d, opt.note)
        st.log(d, "verdict", skill=opt.skill, note=opt.verdict)

    return session.event(change)

#!/usr/bin/env python3
"""One command of a format skill built by AIEditing.

    python tools/run.py check                       profile and copy are intact
    python tools/run.py edit <video> [--topic T]    edit by the profile into <output_dir>/<date>-<topic>/
                       [--out DIR] [--answers F]    exit 3: a decision is needed, see вопросы.json
                       [--screen FILE]              the screen recording when camera and screen are separate
                       [--no-questions]             the person asked for none, in this run or in the profile
    python tools/run.py note <issue folder> "text"  a remark for the next refinement, into отчёт.md
    python tools/run.py hear <video>                what the format's recogniser hears in it: seconds and words
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def _private_python() -> Path:
    """AIEditing's own venv with Pillow/OpenCV (`ae.py doctor` puts them there)."""
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AIEditing" / "venv" / "Scripts" / "python.exe"
    return Path.home() / ".aiediting" / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


if (__name__ == "__main__" and not os.environ.get("AIEDITING_IN_VENV") and sys.prefix == sys.base_prefix
        and _private_python().is_file()):
    sys.exit(subprocess.call([str(_private_python()), str(Path(__file__).resolve()), *sys.argv[1:]],
                             env=dict(os.environ, AIEDITING_IN_VENV="1")))

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
for _p in (str(SKILL), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from approvals import QUESTIONS, NeedsApproval, approver_for  # noqa: E402
from issue import issue_folder  # noqa: E402
from notes import add_note  # noqa: E402
from runtime.profile import load_profile  # noqa: E402


def edit(profile, opt):
    from runtime import pipelines

    src = Path(opt.video).expanduser().resolve()
    if not src.is_file():
        print("Нет такого файла: {}".format(src))
        return 2
    screen = Path(opt.screen).expanduser().resolve() if opt.screen else None
    if screen is not None and not screen.is_file():
        print("Нет такого файла экрана: {}".format(screen))
        return 2
    out = Path(opt.out).resolve() if opt.out else issue_folder(profile, src, opt.topic)
    approve = approver_for(profile, out, Path(opt.answers) if opt.answers else None, opt.no_questions)
    try:
        report = pipelines.run(src, profile, out, approve, **({"screen": screen} if screen else {}))
    except NeedsApproval as e:
        print(str(e))
        print("Папка выпуска: {}".format(out))
        return 3
    (out / QUESTIONS).unlink(missing_ok=True)  # answered: the folder holds the result, not the plan
    print((report or {}).get("handover") or "Готово: {}".format((report or {}).get("output") or out))
    print("Папка выпуска: {}".format(out))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(prog="run.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    e = sub.add_parser("edit")
    e.add_argument("video")
    e.add_argument("--topic")
    e.add_argument("--out")
    e.add_argument("--answers")
    e.add_argument("--screen")
    e.add_argument("--no-questions", action="store_true")
    n = sub.add_parser("note")
    n.add_argument("issue")
    n.add_argument("text")
    h = sub.add_parser("hear")
    h.add_argument("video")
    opt = ap.parse_args(argv)
    profile = load_profile(SKILL / "profile.json")
    if opt.cmd == "check":
        print("{}: профиль в порядке, шаги: {}".format(profile["skill_name"], ", ".join(profile["steps"])))
        return 0
    if opt.cmd == "note":
        print(add_note(Path(opt.issue), opt.text, profile["skill_name"]))
        return 0
    if opt.cmd == "hear":
        from runtime import asr

        cfg = dict(profile["asr"], language=profile["asr"].get("language") or profile.get("language") or "")
        for word in asr.transcribe(Path(opt.video).expanduser().resolve(), cfg).get("words", []):
            if str(word.get("text", "")).strip():
                print("{:7.2f} {}".format(word["start"], str(word["text"]).strip()))
        return 0
    return edit(profile, opt)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

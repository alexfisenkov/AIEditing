"""Argument parsing for ae.py; each command lives in its own module."""
from __future__ import annotations

import argparse
import sys

from . import cmd_design, cmd_media, cmd_profile, cmd_run, cmd_skills, doctor
from .session import CliError

RUNTIME_ERRORS = {"LookError", "RenderError", "MediaError", "AsrError"}


def _sub(sub, name, fn, *args, **flags):
    p = sub.add_parser(name)
    for a in args:
        p.add_argument(a)
    for flag, kw in flags.items():
        p.add_argument("--" + flag.replace("_", "-"), **kw)
    p.set_defaults(fn=fn)
    return p


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="ae.py")
    sub = ap.add_subparsers(dest="cmd")
    _sub(sub, "init", cmd_run.init, mode={"choices": ["new", "refine"], "default": "new"},
         title={}, fresh={"action": "store_true"})
    p = _sub(sub, "stage", cmd_run.stage, "id", note={})
    p.add_argument("status", nargs="?", choices=["done", "skip"])
    _sub(sub, "ask", cmd_run.ask, "kind", note={"required": True})
    _sub(sub, "answered", cmd_run.answered, note={})
    _sub(sub, "finish", cmd_run.finish, result={"required": True})
    _sub(sub, "stop-server", cmd_run.stop_server, delay={"type": float, "default": 0.0})
    _sub(sub, "formats", cmd_profile.cmd_formats, "answer", language={"default": "ru"})
    p = _sub(sub, "profile", cmd_profile.cmd_profile, "action", "skill", video={}, fresh={"action": "store_true"})
    p.add_argument("values", nargs="*")
    _sub(sub, "design-example", cmd_profile.cmd_design_example, "skill")
    _sub(sub, "frames", cmd_media.cmd_frames, "video", n={"type": int, "default": 6})
    _sub(sub, "layout", cmd_media.cmd_layout, "source", set={"action": "append", "default": []},
         with_source={})
    _sub(sub, "samples", cmd_media.cmd_samples, "skill", frame={}, element={"choices": ["chapter", "caption", "card"], "default": "chapter"})
    p = _sub(sub, "choose", cmd_design.cmd_choose, "skill", "element")
    p.add_argument("n", type=int)
    _sub(sub, "trial", cmd_media.cmd_trial, "skill", "video", start={"type": float},
         duration={"type": float}, answers={}, screen={})
    p = _sub(sub, "verdict", cmd_media.cmd_verdict, "skill", note={})
    p.add_argument("verdict", choices=["yes", "no"])
    _sub(sub, "build-skill", cmd_skills.cmd_build, "profile", "dest", replace={"action": "store_true"})
    _sub(sub, "install-skill", cmd_skills.cmd_install, "folder")
    _sub(sub, "list-skills", cmd_skills.cmd_list, json={"action": "store_true"})
    _sub(sub, "backup-skill", cmd_skills.cmd_backup, "name")
    _sub(sub, "restore-skill", cmd_skills.cmd_restore, "name", backup={}, list={"action": "store_true"})
    _sub(sub, "doctor", doctor.cmd_doctor, steps={}, asr={}, install={}, yes={"action": "store_true"},
         catalog={}, requirements={"action": "store_true"})
    return ap


def main(argv) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    opt = parser().parse_args(argv)
    fn = getattr(opt, "fn", cmd_run.sync)
    try:
        out = fn(opt)
    except CliError as e:
        print("ошибка: {}".format(e))
        return 1
    except cmd_media.Waiting as e:
        print(str(e))
        return 3
    except Exception as e:  # a runtime refusal (LookError, RenderError, MediaError…) is one line, not a trace
        if type(e).__name__ not in RUNTIME_ERRORS and not isinstance(e, (ValueError, OSError)):
            raise
        print("ошибка: {}".format(e))
        return 1
    if out:
        print(out)
    return 0

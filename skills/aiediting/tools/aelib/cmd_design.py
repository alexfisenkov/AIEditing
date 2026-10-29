"""The person picks one variant of a design element; it goes into the skill's `design/samples/`."""
from __future__ import annotations

import shutil

import state as st

from . import session
from .session import CliError


def cmd_choose(opt) -> str:
    def change(d):
        w = session.work()
        row = next((s for s in d["design"]["samples"] if (s["skill"], s["element"]) == (opt.skill, opt.element)), None)
        if row is None or not 1 <= opt.n <= len(row["files"]):
            raise CliError("Варианта {} элемента «{}» у {} нет".format(opt.n, opt.element, opt.skill))
        src = w / row["files"][opt.n - 1]
        dst = w / opt.skill / "design" / "samples" / (opt.element + src.suffix)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        d["design"]["chosen"]["{}/{}".format(opt.skill, opt.element)] = {"n": opt.n, "file": st.rel(w, dst)}
        st.log(d, "chosen", skill=opt.skill, note="{}: вариант {}".format(opt.element, opt.n))
        return "Выбран вариант {} «{}» → {}".format(opt.n, opt.element, dst)

    return session.event(change)

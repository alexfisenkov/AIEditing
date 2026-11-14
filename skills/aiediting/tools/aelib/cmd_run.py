"""Workshop bookkeeping: init, stage, ask/answered, finish, and the bare call that re-raises the server."""
from __future__ import annotations

import subprocess
import sys
import time

import state as st
from state.server import _detached

from . import session
from .paths import SKILL_DIR, TOOLS_DIR
from .session import CliError

STOP_DELAY = 12


def init(opt) -> str:
    from runtime import __version__

    w = session.work()
    old = st.read(w)
    if old and not old.get("finishedAt") and not opt.fresh:
        raise CliError("Здесь уже идёт мастерская ({}) — продолжите её (phases/resume.md) "
                       "или начните заново с --fresh".format(old.get("title")))
    st.install_page(w)
    (w / ".gitignore").write_text("*\n", encoding="utf-8")  # frames of a screen and drafts: never into a project's git
    data = st.fresh(opt.mode, opt.title or ("Новый скилл монтажа" if opt.mode == "new" else "Доработка"),
                    __version__)
    data["noQuestions"] = bool(opt.no_questions)
    if old and old.get("intro"):  # what the person told about themselves is not asked again in this folder
        data["intro"] = old["intro"]
    st.log(data, "init", mode=opt.mode)
    line = session.commit(data)
    return "\n".join(["Мастерская: {}".format(w), "Дашборд: {}".format(line)] + _news(__version__))


def _news(version: str):
    """A newer AIEditing on GitHub: one line for the person, at most once a day; silence without the network."""
    try:
        from runtime.updates import workshop_note

        note = workshop_note(version, SKILL_DIR)
    except Exception:  # the check never stops the workshop
        note = None
    return ["Новая версия: " + note] if note else []


def no_questions(opt) -> str:
    """Said in the middle of a workshop: the draft stays, the questions stop."""
    def change(d):
        d["noQuestions"] = True
        st.close_wait(d, "дальше без вопросов")
        st.log(d, "no-questions")

    return session.event(change)


def stage(opt) -> str:
    return session.event(lambda d: st.set_stage(d, opt.id, opt.status or "active", opt.note))


def ask(opt) -> str:
    return session.event(lambda d: st.ask(d, opt.kind, opt.note))


def answered(opt) -> str:
    return session.event(lambda d: st.close_wait(d, opt.note))


def finish(opt) -> str:
    def change(d):
        st.close_wait(d)
        for s in d["stages"]:
            if s["status"] == "active":
                s.update(status="done", endedAt=st.now())
        d["finishedAt"], d["result"] = st.now(), opt.result
        st.log(d, "finish", note=opt.result)

    session.event(change)
    if not session.serving():
        return "мастерская закрыта"
    subprocess.Popen([sys.executable, str(TOOLS_DIR / "ae.py"), "stop-server", "--delay", str(STOP_DELAY)],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     **_detached())
    return "мастерская закрыта; сервер погаснет через {} с — страница успеет забрать финал".format(STOP_DELAY)


def stop_server(opt) -> str:
    time.sleep(max(0.0, opt.delay))
    return st.stop(session.work())


def sync(opt) -> str:
    from runtime import __version__

    data = session.load()
    st.install_page(session.work())      # a workshop begun on an older version gets today's page
    return "\n".join([session.commit(data)] + _news(__version__))

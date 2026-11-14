"""One event of the workshop: load the state, change it, write it, refresh the page, keep the server up."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

import state as st

from .paths import work_dir


class CliError(Exception):
    """A refusal or a failure to tell the agent in one line (exit code 1)."""


def work() -> Path:
    return work_dir()


def serving() -> bool:
    return not os.environ.get("AIEDITING_NO_SERVE")


def load() -> dict:
    data = st.read(work())
    if data is None:
        raise CliError("Мастерская ещё не начата здесь: сначала ae.py init")
    return data


def commit(data: dict) -> str:
    w = work()
    st.save(w, data)
    return show(w, data, st.write_snapshot(w, data))


def show(w: Path, data: dict, page: str = "дашборд обновлён") -> str:
    """Where the dashboard is now: its address, or — with no server — the path of the page itself."""
    why = "мастерская закрыта" if data.get("finishedAt") else None if serving() else "AIEDITING_NO_SERVE"
    if why is None:
        return st.serve(w)
    return "{}, без сервера ({}) — открывается файлом: {}".format(page, why, Path(w).resolve() / "dashboard.html")


def event(change: Callable[[dict], Optional[str]]) -> str:
    """Runs `change` on the state and commits; returns what `change` said, or the server line."""
    data = load()
    said = change(data)
    line = commit(data)
    return said or line


def touch(change: Callable[[dict], None]) -> None:
    """Like event, but silent when there is no workshop here — build and install work without one."""
    data = st.read(work())
    if data is not None:
        change(data)
        commit(data)

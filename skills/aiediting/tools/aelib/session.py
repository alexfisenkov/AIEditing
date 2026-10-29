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
    page = st.write_snapshot(w, data)
    if data.get("finishedAt") or not serving():
        return page
    return st.serve(w)


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

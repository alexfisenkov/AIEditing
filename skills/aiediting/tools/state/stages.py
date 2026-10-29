"""The workshop's stages and waits — the same bookkeeping AISpa keeps, with AIEditing's own stages."""
from __future__ import annotations

from typing import Optional

from .store import log, now

ORDER = ["start", "formats", "sources", "interview", "design", "trial", "build"]
WORDS = {"start": "Старт", "formats": "Форматы", "sources": "Исходники", "interview": "Интервью",
         "design": "Дизайн", "trial": "Пробный монтаж", "build": "Сборка"}
WAIT_KINDS = ("question", "choice", "approve", "trial", "action", "stop")


def fresh(mode: str, title: str, version: str) -> dict:
    t = now()
    stages = [{"id": s, "word": WORDS[s], "status": "pending"} for s in ORDER]
    stages[0].update(status="active", startedAt=t)
    return {"app": "aiediting", "version": version, "mode": mode, "title": title, "startedAt": t,
            "finishedAt": None, "result": None, "stages": stages, "waiting": None, "waits": [],
            "formats": [], "sources": [], "design": {"samples": [], "chosen": {}}, "trials": [],
            "skills": [], "log": []}


def close_wait(state: dict, answer: Optional[str] = None) -> None:
    wait = state.get("waiting")
    if wait:
        state.setdefault("waits", []).append([wait["since"], now()])
        log(state, "answered", kind=wait["kind"], note=answer)
        state["waiting"] = None


def set_stage(state: dict, sid: str, status: str = "active", note: Optional[str] = None) -> None:
    """Opening a stage closes every earlier one still open; `done`/`skip` close just this one."""
    if sid not in ORDER:
        raise ValueError("Нет этапа {!r}; есть: {}".format(sid, ", ".join(ORDER)))
    close_wait(state)
    t, idx = now(), ORDER.index(sid)
    for st in state["stages"]:
        i = ORDER.index(st["id"])
        if status == "active" and i < idx and st["status"] in ("active", "pending"):
            st.update(status="done" if st["status"] == "active" else "skipped", endedAt=t)
        if st["id"] == sid:
            new = {"active": "active", "done": "done", "skip": "skipped"}[status]
            st["status"] = new
            st.setdefault("startedAt", t)
            if new != "active":
                st["endedAt"] = t
            if note:
                st["note"] = note
    log(state, "stage", stage=WORDS[sid], status=status, note=note)


def ask(state: dict, kind: str, note: str) -> None:
    if kind not in WAIT_KINDS:
        raise ValueError("Вид ожидания {!r}; есть: {}".format(kind, ", ".join(WAIT_KINDS)))
    close_wait(state)
    state["waiting"] = {"kind": kind, "note": note, "since": now()}
    log(state, "ask", kind=kind, note=note)

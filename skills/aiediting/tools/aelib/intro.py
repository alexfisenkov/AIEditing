"""`ae.py intro` — what the person told about themselves at the start, kept for the whole road.

The answers live in `state.js` of the workshop folder (never in the repository) and survive `init --fresh` in that folder. Later
phases read them instead of asking again. `intro apply` lays them where they belong: the format's taste lines in its draft, and,
with a library, its files about the person and the list of what is never shown. Nothing is invented: an empty answer stays empty.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Dict, List

import state as st

from . import profiles, session
from .session import CliError

# The nine points of the intro message (phases/start.md, «Get to know the person»): a key each, the eighth split in two.
KEYS = {"computer": "компьютер и диск", "videos": "какие ролики", "camera": "на что снимает и чем пишет звук",
        "program": "программа для монтажа", "blog": "про что блог и для кого", "materials": "свой материал",
        "services": "сервисы", "liked": "ролики, которые нравятся", "disliked": "ролики, которые не нравятся",
        "forbid": "чего нельзя показывать"}
TASTE = {"blog": "Из знакомства, блог и зритель: {}", "liked": "Из знакомства, нравится по монтажу: {}",
         "disliked": "Из знакомства, не нравится по монтажу: {}", "forbid": "Из знакомства, не показывать: {}"}
ABOUT = {"blog": "обо-мне/блог.md", "videos": "обо-мне/кто-я.md", "camera": "обо-мне/кто-я.md"}


def _show(intro: Dict[str, str]) -> str:
    if not intro:
        return "Знакомства ещё не было: ae.py intro set <ключ>=<ответ>; ключи: " + ", ".join(KEYS)
    lines = ["{} ({}): {}".format(k, KEYS[k], intro[k]) for k in KEYS if intro.get(k)]
    gaps = [k for k in KEYS if not intro.get(k)]
    return "\n".join(lines + (["не сказано: " + ", ".join(gaps)] if gaps else []))


def _set(data: dict, values: List[str]) -> str:
    intro = data.setdefault("intro", {})
    for item in values:
        key, sep, text = item.partition("=")
        key = key.strip()
        if not sep or key not in KEYS:
            raise CliError("intro set <ключ>=<ответ>; ключи: {}".format(", ".join(KEYS)))
        if text.strip():
            intro[key] = " ".join(text.split())
        else:
            intro.pop(key, None)
    st.log(data, "intro", note=", ".join(sorted(intro)))
    return _show(intro)


def _to_draft(skill: str, intro: Dict[str, str]) -> List[str]:
    path = session.work() / skill / "profile.json"
    if not path.is_file():
        raise CliError("Черновика {} нет: сначала ae.py formats или ae.py profile open".format(path))
    profile, done = profiles.read(path), []
    known = {row.get("note") for row in profile.get("taste", [])}
    for key, line in TASTE.items():
        note = line.format(intro[key]) if intro.get(key) else None
        if note and note not in known:
            profiles.add_taste(profile, note)
            done.append("{}: вкус «{}»".format(skill, note))
    if done:
        profiles.write(profile, path)
    return done


def _to_library(intro: Dict[str, str]) -> List[str]:
    from runtime.library import find_library, rules, store

    lib = find_library()
    if lib is None:
        return []
    done, day = [], dt.date.today().isoformat()
    for key, rel in ABOUT.items():
        if not intro.get(key):
            continue
        path = Path(lib) / rel
        body = path.read_text(encoding="utf-8") if path.is_file() else ""
        if intro[key] in body:
            continue
        store.write_text(path, body.rstrip("\n") + "\n\n- {} (из знакомства): {}\n".format(day, intro[key]))
        done.append("{}: {}".format(rel, KEYS[key]))
    for what in (w.strip() for w in (intro.get("forbid") or "").split(";")):
        if what:
            done.append("чего-нельзя.md: {}".format(rules.forbid(lib, what)))
    return done


def to_new_draft(skill: str) -> List[str]:
    """`ae.py formats` drafts a format: what the intro said about taste is in it from the start, nothing asked again."""
    data = st.read(session.work())
    intro = (data or {}).get("intro") or {}
    return _to_draft(skill, intro) if intro else []


def apply(skill: str = "") -> List[str]:
    """Taste lines into the draft of `skill`, and the person's own facts into the library when one is connected."""
    data = session.load()
    intro = data.get("intro") or {}
    return (_to_draft(skill, intro) if skill and intro else []) + _to_library(intro)


def cmd_intro(opt) -> str:
    action, rest = (opt.args[0], opt.args[1:]) if opt.args else ("show", [])
    if action == "show":
        return _show(session.load().get("intro") or {})
    if action == "set":
        return session.event(lambda d: _set(d, rest))
    if action == "apply":
        done = apply(rest[0] if rest else "")
        return "\n".join(done) if done else "Раскладывать нечего: всё уже на месте или знакомства не было"
    raise CliError("ae.py intro [show | set <ключ>=<ответ> … | apply [<скилл>]]")

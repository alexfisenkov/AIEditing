"""Is a newer AIEditing out? One line at most, never a question and never an install.

The workshop asks at its start (`ae.py init`, and the bare call that re-raises a workshop); a format skill asks at `run.py check`
and `run.py edit`, about the workshop it was built on. GitHub is asked at most once a day: the answer is kept in
`~/.aiediting/update-check.json` (Windows: `%LOCALAPPDATA%\\AIEditing\\`). No network, a slow or odd answer → silence, nothing kept.
`AIEDITING_NO_UPDATE_CHECK=1` turns it off. The latest release of the repository wins; with no release, the version in
`skills/aiediting/SKILL.md` of the default branch.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from urllib import error, request

REPO = "alexfisenkov/AIEditing"
OFF = "AIEDITING_NO_UPDATE_CHECK"
API_ENV = "AIEDITING_UPDATE_API"  # another address of the same API: tests, a mirror
API = "https://api.github.com"
CACHE = "update-check.json"
DAY = 24 * 3600
TIMEOUT = 3.0   # one request
DEADLINE = 4.0  # the whole check, DNS included: the start never waits longer
RELEASES = "https://github.com/{}/releases".format(REPO)
NONE = "none"  # GitHub answered, and there is nothing to compare: no release and no readable version
NAME = "aiediting"
ROOTS_HOME = (".agents/skills", ".claude/skills", ".codex/skills", ".cursor/skills", ".gemini/skills", ".openclaw/skills")
ROOTS_HERE = (".agents/skills", ".claude/skills", ".gemini/skills", "skills")
_VERSION = re.compile(r"(\d+(?:\.\d+)+)")


def config_dir() -> Path:
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AIEditing"
    return Path.home() / ".aiediting"


def off() -> bool:
    return os.environ.get(OFF, "").strip() not in ("", "0")


def parse(text) -> Optional[Tuple[int, ...]]:
    found = _VERSION.search(str(text or ""))
    return tuple(int(x) for x in found.group(1).split(".")) if found else None


def newer(a, b) -> bool:
    """Is version `a` later than `b`? An unreadable one is never newer, and anything is newer than an unreadable `b`."""
    va, vb = parse(a), parse(b)
    return bool(va) and (vb is None or va > vb)


def _fetch(url: str, accept: str):
    """The body; b"" for 404 (nothing there); None when the network or the server failed."""
    req = request.Request(url, headers={"Accept": accept, "User-Agent": "AIEditing-update-check"})
    try:
        with request.urlopen(req, timeout=TIMEOUT) as answer:
            return answer.read(256 * 1024)
    except error.HTTPError as exc:
        exc.close()
        return b"" if exc.code == 404 else None
    except (error.URLError, OSError, ValueError):
        return None


def _skill_md_version(text: str) -> Optional[str]:
    head = text.split("\n---", 1)[0] if text.startswith("---") else ""
    found = re.search(r"(?m)^\s+version:\s*[\"']?(\d+(?:\.\d+)+)", head)
    return found.group(1) if found else None


def _own_link(url) -> str:
    """Only a page of this repository goes into the agent's context; anything else becomes the list of releases."""
    url = str(url or "")
    return url if url.startswith("https://github.com/{}/".format(REPO)) and not any(c.isspace() for c in url) else RELEASES


def _within_deadline() -> Optional[dict]:
    """`ask_github` in a thread of its own: a hung DNS or a slow server costs the start DEADLINE seconds at most."""
    box = []
    worker = threading.Thread(target=lambda: box.append(ask_github()), daemon=True)
    worker.start()
    worker.join(DEADLINE)
    return box[0] if box else None


def _fresh(kept, now: float) -> bool:
    """A kept answer younger than a day; an unreadable one counts as none and is written over."""
    try:
        return isinstance(kept, dict) and 0 <= now - float(kept.get("checked")) < DAY
    except (TypeError, ValueError):
        return False


def ask_github() -> Optional[dict]:
    """{"version", "url"} of the latest; {} when GitHub has nothing to compare; None when it could not be asked."""
    base = (os.environ.get(API_ENV) or API).rstrip("/")
    body = _fetch("{}/repos/{}/releases/latest".format(base, REPO), "application/vnd.github+json")
    if body is None:
        return None
    if body:
        try:
            data = json.loads(body.decode("utf-8"))
        except ValueError:
            return None
        version = parse(data.get("tag_name")) if isinstance(data, dict) else None
        if version:
            return {"version": ".".join(map(str, version)), "url": _own_link(data.get("html_url"))}
    body = _fetch("{}/repos/{}/contents/skills/aiediting/SKILL.md".format(base, REPO), "application/vnd.github.raw+json")
    if body is None:
        return None
    version = _skill_md_version(body.decode("utf-8", "replace")) if body else None
    return {"version": version, "url": "https://github.com/{}/blob/HEAD/CHANGELOG.md".format(REPO)} if version else {}


def latest(now: Optional[float] = None) -> Optional[dict]:
    """The latest AIEditing GitHub knows of, asked at most once a day; None when off, offline or unknown."""
    if off():
        return None
    now = time.time() if now is None else now
    path = config_dir() / CACHE
    try:
        kept = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        kept = None
    if _fresh(kept, now):
        found = kept.get("latest")
        if isinstance(found, dict) and parse(found.get("version")):
            return dict(found, url=_own_link(found.get("url")))
        return None
    found = _within_deadline()
    if found is None:
        return None  # offline: nothing kept, the next start asks again
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps({"checked": now, "latest": found or NONE}, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass
    return found or None


def _locked(lock: Path) -> bool:
    """Does the lock file of `npx skills` name this skill as one it can update? Its global one is `~/.agents/.skill-lock.json`, a
    project's `skills-lock.json`. A copy added from a local folder (`sourceType: local`) is not updated by `npx skills update`."""
    try:
        data = json.loads(lock.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    skills = data.get("skills") if isinstance(data, dict) else None
    if isinstance(skills, dict):
        entry = skills.get(NAME)
        return entry is not None and not (isinstance(entry, dict) and entry.get("sourceType") == "local")
    return (NAME in skills) if isinstance(skills, list) else False


def _global_locks() -> List[Path]:
    state = os.environ.get("XDG_STATE_HOME", "").strip()
    return ([Path(state) / "skills" / ".skill-lock.json"] if state else []) + [Path.home() / ".agents" / ".skill-lock.json"]


def how_to_update(skill_dir) -> str:
    """The exact way to update this copy: a clone pulls; a copy `npx skills` installed and still records updates by it; anything
    else, a copy laid by hand included, is reinstalled."""
    real = Path(skill_dir).resolve()
    repo = real.parent.parent
    if real.parent.name == "skills" and (repo / ".git").exists():
        return 'git -C "{}" pull'.format(repo)
    home = Path.home().resolve()
    if real == (home / ".agents" / "skills" / NAME).resolve() and any(_locked(lock) for lock in _global_locks()):
        return "npx skills update {} -g".format(NAME)
    project = real.parent.parent.parent
    if (real.parent.name == "skills" and real.parent.parent.name == ".agents" and project != home
            and _locked(project / "skills-lock.json")):
        return "npx skills update {}".format(NAME)
    return "переустановить: npx skills add {} --skill {} -g".format(REPO, NAME)


def workshop_note(version: str, skill_dir) -> Optional[str]:
    """For the workshop itself: a newer release → one line for the person, said once at the start."""
    found = latest()
    if not found or not newer(found["version"], version):
        return None
    return ("AIEditing {} (у вас {}). Обновить эту копию: {}; после обновления нужна новая сессия. "
            "Что нового: {}".format(found["version"], version, how_to_update(skill_dir), _own_link(found.get("url"))))


def _versions_in(roots: Iterable[Path]) -> List[str]:
    found = []
    for root in roots:
        init = root / NAME / "runtime" / "__init__.py"
        try:
            text = init.read_text(encoding="utf-8")
        except OSError:
            continue
        hit = re.search(r"__version__\s*=\s*[\"']([^\"']+)", text)
        if hit and parse(hit.group(1)):
            found.append(hit.group(1))
    return found


def workshop_on_computer() -> Optional[str]:
    """The newest AIEditing installed here, in the folders the agents read skills from."""
    home, here = Path.home(), Path.cwd()
    versions = _versions_in([home / r for r in ROOTS_HOME] + [here / r for r in ROOTS_HERE])
    return max(versions, key=parse) if versions else None


def format_note(built: str, skill_name: str) -> Optional[str]:
    """For a format skill: the workshop it was built on is older than the one installed or the one released."""
    if off() or not parse(built):
        return None
    # the workshop starts only when called by name (disable-model-invocation, Codex: allow_implicit_invocation false)
    again = ("запустите AIEditing (/aiediting в Claude Code, $aiediting в Codex) и выберите доработку {}, чтобы пересобрать скилл "
             "на новой версии".format(skill_name))
    local = workshop_on_computer()
    if local and newer(local, built):
        return "Мастерская обновилась до {} (скилл собран на {}) — {}.".format(local, built, again)
    found = latest()
    newest_here = local if local and newer(local, built) else built
    if found and newer(found["version"], newest_here):
        return ("Вышла AIEditing {} (скилл собран на {}) — обновите AIEditing и {}.".format(found["version"], built, again))
    return None

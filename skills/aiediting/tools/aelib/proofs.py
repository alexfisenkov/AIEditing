"""Is what the interview chose there in fact? A warning for each choice the disk does not back, before the build.

`phases/interview.md`, «The proof, by a fact»: a chosen step that cannot work today is taken out, not left dead in the profile. These
are warnings, not refusals: `ae.py profile check` and `build-skill` name them, the agent proves or removes. A key is only looked for,
never printed. A profile without the new steps gives none, as before.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}


def _folder(raw) -> Optional[str]:
    if isinstance(raw, str):
        return raw
    return (raw or {}).get("dir") if isinstance(raw, dict) else None


def _tracks(path: Path) -> bool:
    return path.is_dir() and any(p.is_file() and p.suffix.lower() in AUDIO for p in path.rglob("*"))


def _broll() -> List[str]:
    from runtime.library import find_library, inventory

    lib = find_library()
    if lib is None:
        return ["broll: библиотека не подключена (ae.py library set <папка>) — вставкам и стокам неоткуда браться"]
    if not inventory.load(lib):
        return ["broll: в описи библиотеки нет ни одного файла — опишите первый лист (ae.py library scan, sheet, describe)"]
    return []


def _music(params: dict) -> List[str]:
    raw = params.get("music")
    folder = _folder(raw)
    if folder:
        path = Path(folder).expanduser()
        if not path.is_dir():
            return ["music: папки с треками нет: {}".format(folder)]
        if not _tracks(path):
            return ["music: в папке {} нет ни одного трека".format(folder)]
        return []
    if isinstance(raw, dict) and raw.get("service"):
        return []
    return ["music: не задана папка с треками (params.music.dir) и нет сервиса — музыке неоткуда браться"]


def _voice(params: dict) -> List[str]:
    from runtime.asr.contract import AsrError
    from runtime.asr.secrets import read_key

    spec = params.get("voice")
    name = (spec.get("key_env") if isinstance(spec, dict) else None) or "AUPHONIC_API_KEY"
    try:
        read_key(name)  # only whether it is there; the value goes nowhere
    except AsrError:
        return ["voice_clean: ключа нет в переменной {} (окружение или .env) — проверка: ae.py voice-try <скилл> --check".format(name)]
    return []


def _angles(draft: Optional[Path]) -> List[str]:
    if draft is None:
        return []
    for report in sorted(draft.glob("trials/*/out/отчёт.md")):
        try:
            if "Сдвиг по звуку" in report.read_text(encoding="utf-8"):
                return []
        except OSError:
            continue
    return ["angles: ни одна проба не прошла с несколькими камерами — ae.py trial <скилл> <главная камера> --camera <файл> "
            "[--audio <рекордер>]"]


def unproved(profile: dict, draft: Optional[Path] = None) -> List[str]:
    """What the profile chose and the disk does not back yet; `draft` is the draft's folder, for the trials of cameras."""
    steps, params, found = set(profile.get("steps") or []), profile.get("params") or {}, []
    if "broll" in steps:
        found += _broll()
    if "music" in steps:
        found += _music(params)
    if "voice_clean" in steps:
        found += _voice(params)
    if "angles" in steps:
        found += _angles(draft)
    sfx = _folder(params.get("sfx"))
    if sfx and not Path(sfx).expanduser().is_dir():
        found.append("params.sfx: папки со звуками нет: {}".format(sfx))
    return found


def said(found: List[str]) -> str:
    if not found:
        return ""
    return ("\nНе доказано фактом (до сборки доказать или убрать шаг, phases/interview.md):\n- " + "\n- ".join(found))

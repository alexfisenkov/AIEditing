"""`ae.py voice-try` — a minute of the person's recording through each of our Auphonic presets, side by side on the
dashboard with the sound as recorded, so the preset is chosen by ear once; `--check` only asks whether the key works.
Every processing is a paid request on the person's own key: it runs only when the profile has the step `voice_clean`,
and the same piece with the same preset is processed once (the ready file is taken again)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .session import CliError, work

STEP = "voice_clean"


def _steps(skill: str) -> list:
    try:
        return list(json.loads((work() / skill / "profile.json").read_text(encoding="utf-8")).get("steps") or [])
    except (OSError, ValueError, AttributeError):
        return []


def _stamp(src: Path, start: float, duration, preset) -> str:
    st = src.stat()
    raw = json.dumps([str(src), st.st_size, int(st.st_mtime), start, duration, preset], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _clean(auphonic, original: Path, preset, out: Path, stamp: str) -> bool:
    """The clean sound of one preset; True when it was paid for now, False when the ready file was taken."""
    mark = out.with_suffix(".json")
    try:
        if out.is_file() and json.loads(mark.read_text(encoding="utf-8")).get("stamp") == stamp:
            return False
    except (OSError, ValueError, AttributeError):
        pass
    auphonic.process(original, preset, out)
    mark.write_text(json.dumps({"stamp": stamp}), encoding="utf-8")
    return True


def _try(opt) -> str:
    from runtime.pipelines import voice
    from runtime.services import auphonic

    from . import trial

    if opt.check:
        return auphonic.check_key()
    if not opt.video:
        raise CliError("Нужно видео с голосом: ae.py voice-try <skill> <видео> [--start S] [--duration 60]")
    if STEP not in _steps(opt.skill):
        raise CliError("Проба голоса — платная обработка в Auphonic, она делается только для выбранной чистки: сначала "
                       "добавьте шаг {0} в steps профиля {1} (ae.py profile set {1} 'steps=[…, \"{0}\"]'), потом повторите "
                       "voice-try. Проверить ключ без оплаты: ae.py voice-try {1} --check".format(STEP, opt.skill))
    src = Path(opt.video).expanduser().resolve()
    if not src.is_file():
        raise CliError("Нет такого файла: {}".format(src))
    folder = work() / opt.skill / "голос"
    folder.mkdir(parents=True, exist_ok=True)
    start = opt.start or 0.0
    piece = trial._piece(src, folder, start, opt.duration, "кусок")
    original = voice.extract(piece, folder / voice.ORIGINAL)
    shown, paid = [("как-записано", "как записано", piece)], 0
    for name, preset in voice.PRESETS.items():
        clean = folder / "{}.wav".format(name)
        paid += _clean(auphonic, original, preset, clean, _stamp(src, start, opt.duration, preset))
        shown.append((name, name, voice.mux(piece, clean, folder / "голос-{}{}".format(name, piece.suffix or ".mp4"))))
    for ident, title, video in shown:
        trial._on_dashboard(opt.skill, folder, video, {"id": "голос-" + ident, "title": "Голос · " + title})
    return ("На дашборде рядом: {}. Послушайте одно и то же место и скажите, какой берём.\n"
            "Выбранный записывается так: ae.py profile set {} 'params.voice={{\"service\": \"auphonic\", \"preset\": \"<имя>\"}}'.\n"
            "Auphonic считает каждую обработку минимум за 3 мин: сейчас ушло {} мин из кредитов человека{}.").format(
        ", ".join("«{}»".format(t) for _, t, _ in shown), opt.skill, 3 * paid,
        "" if paid else " (тот же кусок уже обработан, взяты готовые файлы)")


def cmd_voice_try(opt) -> str:
    from runtime.services.web import ServiceError

    try:
        return _try(opt)
    except ServiceError as exc:
        raise CliError(str(exc))

"""`ae.py voice-try` — a minute of the person's recording through each of our Auphonic presets, side by side on the
dashboard with the sound as recorded, so the preset is chosen by ear once; `--check` only asks whether the key works.
Every run is a paid request on the person's own key: the workshop runs it only after they chose Auphonic."""
from __future__ import annotations

from pathlib import Path

from .session import CliError, work


def _try(opt) -> str:
    from runtime.pipelines import voice
    from runtime.services import auphonic

    from . import trial

    if opt.check:
        return auphonic.check_key()
    if not opt.video:
        raise CliError("Нужно видео с голосом: ae.py voice-try <skill> <видео> [--start S] [--duration 60]")
    src = Path(opt.video).expanduser().resolve()
    if not src.is_file():
        raise CliError("Нет такого файла: {}".format(src))
    folder = work() / opt.skill / "голос"
    folder.mkdir(parents=True, exist_ok=True)
    piece = trial._piece(src, folder, opt.start or 0.0, opt.duration, "кусок")
    original = voice.extract(piece, folder / voice.ORIGINAL)
    shown = [("как-записано", "как записано", piece)]
    for name, preset in voice.PRESETS.items():
        clean = auphonic.process(original, preset, folder / "{}.wav".format(name))
        shown.append((name, name, voice.mux(piece, clean, folder / "голос-{}{}".format(name, piece.suffix or ".mp4"))))
    for ident, title, video in shown:
        trial._on_dashboard(opt.skill, folder, video, {"id": "голос-" + ident, "title": "Голос · " + title})
    return ("На дашборде рядом: {}. Послушайте одно и то же место и скажите, какой берём.\n"
            "Выбранный записывается так: ae.py profile set {} 'params.voice={{\"service\": \"auphonic\", \"preset\": \"<имя>\"}}' "
            "и шаг voice_clean в steps.\n"
            "Auphonic считает каждую обработку минимум за 3 мин: эта проба — {} мин из кредитов человека.").format(
        ", ".join("«{}»".format(t) for _, t, _ in shown), opt.skill, 3 * len(voice.PRESETS))


def cmd_voice_try(opt) -> str:
    from runtime.services.web import ServiceError

    try:
        return _try(opt)
    except ServiceError as exc:
        raise CliError(str(exc))

"""`prepare`: checks first, then the working folder: template, working copies, words, face track, design, sound."""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

from . import design as design_mod
from . import face, media, scaffold, sounds, words
from .common import ToolError, need, run, say, fmt_secs

MIN_FREE_GB = 8.0
NODE_MIN = 18


def icloud_roots() -> list:
    home = Path.home()
    return [home / "Documents", home / "Desktop", home / "Library" / "Mobile Documents"]


def check_work_dir(arg: str) -> Path:
    """Absolute, outside iCloud's reach on macOS, with space to render."""
    work = Path(arg).expanduser()
    if not work.is_absolute():
        raise ToolError("Рабочая папка должна быть абсолютным путём, а передано: {}".format(arg))
    if sys.platform == "darwin":
        resolved = Path(os.path.realpath(str(work)))
        for root in icloud_roots():
            real = Path(os.path.realpath(str(root)))
            if resolved == real or real in resolved.parents:
                raise ToolError("Рабочая папка {} внутри {}: iCloud выгружает оттуда файлы, и рендер зависает на 0 % процессора. "
                                "Возьмите, например, ~/.local/share/overlay-kit/<имя>.".format(work, root))
    anchor = work
    while not anchor.exists() and anchor != anchor.parent:
        anchor = anchor.parent
    need_gb = float(os.environ.get("OVERLAY_MIN_FREE_GB", MIN_FREE_GB))
    free_gb = shutil.disk_usage(str(anchor)).free / 1e9
    if free_gb < need_gb:
        raise ToolError("Свободно {:.1f} ГБ, нужно не меньше {:g} ГБ (рендер и копии занимают место).".format(free_gb, need_gb))
    return work


def check_node() -> None:
    need("node", "npm")
    version = run(["node", "-v"], "Версия node").stdout.strip()
    found = re.match(r"v(\d+)", version)
    if found and int(found.group(1)) < NODE_MIN:
        raise ToolError("Нужен Node {}+ (сейчас {}).".format(NODE_MIN, version))


def install_packages(work: Path) -> None:
    if (work / "node_modules" / "remotion").is_dir():
        say("Пакеты уже стоят.")
        return
    if not (work / "package-lock.json").is_file():
        raise ToolError("В рабочей папке нет package-lock.json: ставить по закреплённым версиям нечем.")
    say("Ставлю пакеты по package-lock.json (npm ci)...")
    run([shutil.which("npm") or "npm", "ci", "--no-audit", "--no-fund", "--ignore-scripts"], "Установка пакетов", cwd=work, capture=False)


def run_prepare(args) -> int:
    video = Path(args.video).expanduser()
    work = check_work_dir(args.work)
    need("ffmpeg", "ffprobe")
    if not args.no_install:
        check_node()
    info = media.probe(video)
    speech = Path(args.speech).expanduser() if getattr(args, "speech", None) else None
    media.check_16x9(info, need_sound=speech is None)
    if speech is not None:
        media.check_speech(speech, info["duration"])
    design_mod.check(Path(args.design))  # a broken design or wrong words stop here, before any file is written
    words.check_words(Path(args.words).expanduser(), info["duration"])

    scaffold.deploy_template(work)
    track = work / "src" / "data" / "face.json"
    kept = track.read_bytes() if getattr(args, "keep_face", False) and track.is_file() else None
    replaced = media.make_copies(video, info, work, speech)
    n_words = words.install_words(Path(args.words).expanduser(), info["duration"], work)
    if kept is not None:  # after edits by markers the scenes stay in the seconds of the accepted video, and the face is read in them
        track.write_bytes(kept)
    face_note = face.build_track(work / "public" / "clips" / "source.mp4", work, again=replaced and kept is None)
    logo = scaffold.add_logo(work, args.logo)
    design_note = design_mod.build(Path(args.design), work, logo)
    copied = 0
    if args.sfx:
        copied, _ = sounds.add_sfx(work, Path(args.sfx))
    if args.music:
        sounds.add_music(work, Path(args.music))
    manifest = sounds.write_manifest(work)
    scaffold.set_duration(work, info["duration"])
    scaffold.write_index(work)
    scaffold.install_helpers(work)
    if not args.no_install:
        install_packages(work)

    say("")
    say("Готово: " + str(work))
    say("Длительность {}, кадр {}x{}, слов в файле: {}".format(fmt_secs(info["duration"]), info["width"], info["height"], n_words))
    say("Лицо: " + face_note)
    say("Дизайн: " + design_note)
    say("Логотип: " + (logo or "не передан (угловой знак не показывается)"))
    say("Звуки: {} файлов{}; музыка: {}".format(len(manifest["files"]), " (из --sfx: {})".format(copied) if copied else "", manifest["music"] or "нет"))
    say("Дальше: прочитайте raw/words.txt целиком, разметьте главы в src/data/layouts.ts, напишите сцены.")
    return 0

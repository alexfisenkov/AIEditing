#!/usr/bin/env python3
"""One command of a format skill built by AIEditing.

    python tools/run.py check                       profile and copy are intact
    python tools/run.py check --tools               verify selected local dependencies, no install
    python tools/run.py setup                       repair selected local dependencies and verify
    python tools/run.py edit <video> [--topic T]    edit by the profile into <output_dir>/<date>-<topic>/
                       [--out DIR] [--answers F]    exit 3: a decision is needed, see вопросы.json
                       [--screen FILE]              the screen recording when camera and screen are separate
                       [--camera FILE]… [--audio FILE]  more cameras and the sound recorded apart (step angles)
                       [--no-questions]             the person asked for none, in this run or in the profile
    python tools/run.py note <issue folder> "text" [--format [F]]  a remark: into отчёт.md and, with a library,
                                                    into the person's rules (--format: this format's section)
    python tools/run.py forbid "who or what"        never show this again: into the library's «чего нельзя»
    python tools/run.py library <command> …         the person's library, as `ae.py library` (where, scan, sheet, find…)
    python tools/run.py hear <video> [--from S --to E]  what the format's recogniser hears, in seconds of that file
    python tools/run.py subtitles <issue folder> [--answers F]  the corrections of ответы.json again on the .srt and the words file, no render
    python tools/run.py covers <issue folder> --text "2–4 words" [--more]  six covers from обложки/кадры (none there:
                                                    the sharpest frames of the issue's video) and a sheet;
                                                    --more: six more, nothing overwritten
    python tools/run.py prep "<тема>" [--steps 8] [--out DIR]  подготовка.md before a shoot: the map of 7–12 steps, the camera, the checklist;
                                                    a map beside the source gives the chapters of the edit
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def _private_python() -> Path:
    """Prefer the modern private toolkit; keep the legacy environment for older installs."""
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        root = Path(os.environ["LOCALAPPDATA"]) / "AIEditing"
    else:
        root = Path.home() / ".aiediting"
    tail = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    modern, legacy = root / "toolkit-venv" / tail, root / "venv" / tail
    return modern if modern.is_file() and (root / "toolkit-venv" / "toolkit.ready").is_file() else legacy


if (__name__ == "__main__" and not os.environ.get("AIEDITING_IN_VENV") and _private_python().is_file()
        and Path(sys.prefix).resolve() != _private_python().parent.parent.resolve()):
    sys.exit(subprocess.call([str(_private_python()), str(Path(__file__).resolve()), *sys.argv[1:]],
                             env=dict(os.environ, AIEDITING_IN_VENV="1")))

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
for _p in (str(SKILL), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from aelib.checks import refresh_path

refresh_path()
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from approvals import QUESTIONS, NeedsApproval, approver_for  # noqa: E402
from issue import issue_folder  # noqa: E402
from notes import add_note, remember  # noqa: E402
from runtime.profile import load_profile  # noqa: E402


def toolkit(profile, argv, check_only=False):
    """Use only this built skill's pinned tool rows and installers, never a parent skill path."""
    import json
    from aelib import catalog, setup
    from aelib.checks import current_os
    from aelib.session import CliError

    try:
        pins = json.loads((SKILL / "pins.json").read_text(encoding="utf-8"))
        rows = catalog.tools()
        ids = list(pins["tools"])
    except (OSError, ValueError, KeyError) as exc:
        print("Не готово: повреждён комплект установки: {}".format(exc))
        return 1
    if pins.get("steps") != profile["steps"]:
        print("Профиль и pins.json расходятся по шагам; пересоберите скилл через AIEditing")
        return 2
    if not check_only:
        # The bundled catalog contains only selected tools and their prerequisites.
        pip_needed = any((row.get("install", {}).get(current_os()) or {}).get("kind") == "pip"
                         for row in rows.values())
        if pip_needed:
            from aelib.bootstrap import ensure_python

            try:
                python = ensure_python()
            except CliError as exc:
                print("Не готово: {}".format(exc))
                return 1
            if Path(sys.prefix).resolve() != python.parent.parent.resolve():
                return subprocess.call([str(python), "-B", str(Path(__file__).resolve()), *argv],
                                       env=dict(os.environ, AIEDITING_IN_VENV="1"))
    try:
        print(setup.ensure_tools(ids, check_only=check_only))
    except (CliError, OSError, KeyError, ValueError) as exc:
        print("Не готово: {}".format(exc))
        return 1
    return 0


def edit(profile, opt):
    from runtime import pipelines
    from runtime.services.web import ServiceError

    src = Path(opt.video).expanduser().resolve()
    if not src.is_file():
        print("Нет такого файла: {}".format(src))
        return 2
    screen = Path(opt.screen).expanduser().resolve() if opt.screen else None
    if screen is not None and not screen.is_file():
        print("Нет такого файла экрана: {}".format(screen))
        return 2
    extra = {"screen": screen} if screen else {}
    cameras = [Path(c).expanduser().resolve() for c in opt.camera or []]
    audio = Path(opt.audio).expanduser().resolve() if opt.audio else None
    for path in cameras + ([audio] if audio else []):
        if not path.is_file():
            print("Нет такого файла: {}".format(path))
            return 2
    if cameras:
        extra["cameras"] = cameras
    if audio:
        extra["audio"] = audio
    out = Path(opt.out).resolve() if opt.out else issue_folder(profile, src, opt.topic)
    library_news()
    map_news(src, out)
    approve = approver_for(profile, out, Path(opt.answers) if opt.answers else None, opt.no_questions)
    try:
        report = pipelines.run(src, profile, out, approve, **extra)
    except NeedsApproval as e:
        print(str(e))
        print("Папка выпуска: {}".format(out))
        return 3
    except ServiceError as e:  # the message says why and what to do, never the key; a traceback helps nobody here
        print("Не сделано: {}".format(" ".join(str(e).split())))
        return 1
    (out / QUESTIONS).unlink(missing_ok=True)  # answered: the folder holds the result, not the plan
    print((report or {}).get("handover") or "Готово: {}".format((report or {}).get("output") or out))
    print("Папка выпуска: {}".format(out))
    return 0


def library_news():
    """New files in the folders the library already knows: measured now, described by the agent later."""
    try:
        from runtime.library import find_library, inventory

        lib = find_library()
        if lib is None:
            return
        for kind in inventory.KINDS:
            rows = inventory.scan(lib, kind, [])
            if rows:
                print("Библиотека: новых файлов «{}» — {}; опишите: run.py library sheet {}".format(kind, len(rows), kind))
    except Exception as exc:  # the library never stops an edit
        print("Библиотека не просмотрена: {}".format(exc))


PREP = "подготовка.md"
PREP_TEXT = """# Подготовка к съёмке: {topic}

## Карта ролика

Человек рассказывает по карте; монтаж потом делит ролик на главы по её шагам. Названия шагов — коротко, 2–5 слов.

{steps}
## Куда поставить камеру

Сдвиньте камеру так, чтобы перед лицом или над головой оставалось свободное место: туда лягут анимации. Главный ракурс — по пояс или по грудь, глаза на уровне объектива. Вторая камера сбоку, если она есть, тоже со свободным местом перед лицом.

## Что подготовить для вставок

- что покажете на экране (программы, сайты, файлы) — откройте до записи;
- примеры из жизни: есть ли под них ваши фото и видео? Нет — доснимите до или после;
- цифры: проверьте, что они правдивые и свежие.

## Чек-лист перед записью

- камеры: батареи, карты памяти, одна частота кадров, фокус на лице, экспозиция зафиксирована;
- звук: петличка заряжена, пробная запись 10 секунд прослушана;
- свет включён, мерцания нет; фон убран, ничего личного в кадре; телефон в авиарежиме;
- хлопок в ладоши в начале записи (для синхрона камер и отдельного звука).

## Во время записи

Сбились — пауза 2–3 секунды и фраза заново. Запись не останавливайте: неудачный дубль вырежет монтаж, а пауза перед новым помогает его найти.
"""


def prep(profile, opt):
    """The skeleton of the map and the lists; the steps are written with the person (method `prep`), never by the code."""
    if not 7 <= opt.steps <= 12:
        print("Шагов в карте от 7 до 12, а здесь {}".format(opt.steps))
        return 2
    folder = Path(opt.out).expanduser().resolve() if opt.out else issue_folder(profile, Path(opt.topic), opt.topic)
    path = folder / PREP
    if path.exists():
        print("Уже есть: {} — правьте его, я не перезаписываю".format(path))
        return 0
    steps = "".join("{}. [шаг {} — впиши название]\n   - [о чём сказать]\n   - [о чём сказать]\n   - [о чём сказать]\n".format(i, i)
                    for i in range(1, opt.steps + 1))
    folder.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(PREP_TEXT.format(topic=opt.topic.strip(), steps=steps), encoding="utf-8")
    tmp.replace(path)
    print("Подготовка: {}".format(path))
    print("Заполните карту вместе с человеком; после съёмки положите файл рядом с записью — главы возьмутся из неё")
    return 0


def map_news(src, out):
    """A map of the shoot beside the source (or in the issue folder) names the chapters of this edit."""
    import re

    for path in (Path(src).parent / PREP, Path(out) / PREP):
        if not path.is_file():
            continue
        body = path.read_text(encoding="utf-8").split("## Карта ролика", 1)[-1].split("\n## ", 1)[0]
        titles = [m.group(1).strip() for m in re.finditer(r"(?m)^\d+\.\s+(.+)$", body) if not m.group(1).lstrip().startswith("[")]
        if titles:
            print("Карта съёмки {}: главы ролика по её шагам — {}".format(path, "; ".join(titles)))
        return


def subtitles(profile, opt):
    import json
    from runtime.pipelines.subtitles import rewrite

    issue = Path(opt.issue).expanduser().resolve()
    answers = Path(opt.answers).expanduser().resolve() if opt.answers else issue / "ответы.json"
    if not answers.is_file():
        print("Нет файла с правками: {}".format(answers))
        return 2
    try:
        answer = json.loads(answers.read_text(encoding="utf-8")).get("srt")
        if isinstance(answer, dict) and set(answer) - {"ok", "payload"}:
            raise ValueError("Ответ srt: только ok и payload, правки — внутри payload")
        ok = answer.get("ok", True) if isinstance(answer, dict) else False
        done = rewrite(issue, (profile.get("params") or {}).get("glossary") or {}, (answer.get("payload") if ok else None) or {})
    except (FileNotFoundError, ValueError) as e:
        print(str(e))
        return 2
    said = "Субтитры{} переписаны: правок {}".format(" и слова" if done["words_file"] else "", len(done["fixes"]))
    print(said)
    add_note(issue, "run.py subtitles: {}, не применились: {}".format(said, len([r for r in done["missed"] if not r.get("soft")])), profile["skill_name"])
    for row in done["missed"]:
        print("{}: «{}» → «{}»{}".format("Проверьте" if row.get("soft") else "Не применилась", row["from"], row["to"], ": " + row["why"] if row["why"] else ""))
    return 1 if any(not r.get("soft") for r in done["missed"]) else 0


def covers(profile, opt):
    """Six covers in the format's design from the frames the publishing pack chose; the words are the person's."""
    from runtime.media import covers as cv
    from runtime.render import RenderError, default_design

    issue = Path(opt.issue).expanduser().resolve()
    out = issue / "обложки"
    frames = sorted((out / "кадры").glob("*.jpg")) or _frames_of_video(issue, out / "кадры")
    if not frames:
        print("Нет кадров для обложек в {} и нет ролика в {}: сначала монтаж с шагом publish_pack".format(out / "кадры", issue))
        return 2
    if not 2 <= len(opt.text.split()) <= 4:
        print("Внимание: на обложке читается 2–4 слова, а здесь {}".format(len(opt.text.split())))
    design = SKILL / (profile.get("design") or "design")
    design = design if (design / "tokens.json").is_file() else default_design()
    try:
        ordered = cv.order(frames)
        if not opt.more:
            cv.clear(out)
        made = cv.render(ordered, opt.text, design, out, first=cv.next_number(out) if opt.more else 1)
        sheet = cv.sheet(sorted(p for p in out.glob("обложка-*.jpg") if cv.NAME.match(p.name)), out / "лист.jpg")
    except (ValueError, OSError, RenderError) as e:
        print("Обложки не сделаны: {}".format(e))
        return 1
    for path in made:
        print(path)
    print("Лист: {} (превью 320 px — в {})".format(sheet, out / "превью"))
    print("Сделать ещё шесть? python tools/run.py covers \"{}\" --text \"{}\" --more".format(issue, opt.text))
    return 0


def _frames_of_video(issue, folder):
    """No frames from the publishing pack: the sharpest frames of the issue's video (the largest one), spread over it."""
    from runtime.media import MediaError, covers as cv, probe

    videos = [p for p in issue.glob("*") if p.is_file() and p.suffix.lower() in (".mp4", ".mov", ".m4v", ".mkv", ".webm")]
    if not videos:
        return []
    video = max(videos, key=lambda p: (p.stat().st_size, p.name))
    try:
        made = cv.grab(video, cv.more_moments(video, [], probe(video)["duration"]), folder)
    except MediaError as e:
        print("Кадры из ролика {} не взяты: {}".format(video.name, e))
        return []
    print("Кадров пакета публикации не было: взял {} из ролика {}".format(len(made), video.name))
    return [p for p, _t in made]


def hear(profile, opt):
    import tempfile
    from runtime import asr, media

    cfg = dict(profile["asr"], language=profile["asr"].get("language") or profile.get("language") or "")
    video, start = Path(opt.video).expanduser().resolve(), 0.0
    with tempfile.TemporaryDirectory(prefix="aiediting-") as tmp:
        if opt.start is not None or opt.end is not None:  # a narrow piece, to hear a doubtful place at the speed of the recording
            start = opt.start or 0.0
            video = media.cut_spans(video, [(start, opt.end if opt.end is not None else media.probe(video)["duration"])], Path(tmp) / "кусок.mp4")
        for word in asr.transcribe(video, cfg).get("words", []):
            if str(word.get("text", "")).strip():
                print("{:7.2f} {}".format(word["start"] + start, str(word["text"]).strip()))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(prog="run.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--tools", action="store_true")
    sub.add_parser("setup")
    e = sub.add_parser("edit")
    e.add_argument("video")
    e.add_argument("--topic")
    e.add_argument("--out")
    e.add_argument("--answers")
    e.add_argument("--screen")
    e.add_argument("--camera", action="append", help="another camera of the same scene; may be given several times")
    e.add_argument("--audio", help="the sound recorded apart: it replaces the camera's")
    e.add_argument("--no-questions", action="store_true")
    n = sub.add_parser("note")
    n.add_argument("issue")
    n.add_argument("text")
    n.add_argument("--format", nargs="?", const=True, help="this format's section of the rules, or the named one")
    f = sub.add_parser("forbid")
    f.add_argument("what")
    lib = sub.add_parser("library")
    lib.add_argument("args", nargs=argparse.REMAINDER)
    h = sub.add_parser("hear")
    h.add_argument("video")
    h.add_argument("--from", dest="start", type=float)
    h.add_argument("--to", dest="end", type=float)
    s = sub.add_parser("subtitles")
    s.add_argument("issue")
    s.add_argument("--answers")
    pr = sub.add_parser("prep")
    pr.add_argument("topic")
    pr.add_argument("--steps", type=int, default=8)
    pr.add_argument("--out")
    cv = sub.add_parser("covers")
    cv.add_argument("issue")
    cv.add_argument("--text", required=True)
    cv.add_argument("--more", action="store_true")
    opt = ap.parse_args(argv)
    if opt.cmd == "library":
        from runtime.library.cli import main as library

        return library(list(opt.args))
    if opt.cmd == "forbid":
        from runtime.library.cli import main as library

        return library(["forbid", opt.what])
    profile = load_profile(SKILL / "profile.json")
    if opt.cmd == "check":
        if opt.tools:
            return toolkit(profile, argv, check_only=True)
        print("{}: профиль в порядке, шаги: {}".format(profile["skill_name"], ", ".join(profile["steps"])))
        return 0
    if opt.cmd == "setup":
        return toolkit(profile, argv)
    if opt.cmd == "note":
        fmt = profile["format"] if opt.format is True else opt.format
        print(remember(Path(opt.issue), opt.text, profile["skill_name"], fmt))
        return 0
    if opt.cmd == "hear":
        return hear(profile, opt)
    if opt.cmd == "subtitles":
        return subtitles(profile, opt)
    if opt.cmd == "covers":
        return covers(profile, opt)
    if opt.cmd == "prep":
        return prep(profile, opt)
    return edit(profile, opt)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

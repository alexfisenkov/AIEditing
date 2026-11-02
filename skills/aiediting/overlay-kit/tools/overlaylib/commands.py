"""The small commands: frame, draft, sheets, empties, texts, frames, sync, index, example."""
from __future__ import annotations

from pathlib import Path

from . import remotion, scaffold, scanning, sheets, verify
from .common import ToolError, need, parse_secs, say, work_dir
from .media import duration_of


def cmd_frame(args) -> int:
    work = work_dir(args.work)
    remotion.ready(work)
    if not args.seconds:
        raise ToolError("Укажите секунды кадров, например: overlay.py frame <папка> 9 16.5")
    seconds = parse_secs(args.seconds, remotion.duration(work))
    for sec in seconds:
        out = work / "out" / "frames" / "{}.jpg".format(sec)
        remotion.still(work, sec, out)
        say(str(out))
    return 0


def cmd_draft(args) -> int:
    work = work_dir(args.work)
    remotion.ready(work)
    remotion.typecheck(work)
    remotion.render(work, work / "out" / "draft.mp4", draft=True)
    return 0


def cmd_sheets(args) -> int:
    need("ffmpeg")
    made = sheets.contact_sheets(Path(args.video).expanduser(), Path(args.folder).expanduser(), args.step)
    for m in made:
        say(str(m))
    say("Листов: {} (по 30 кадров, шаг {:g} с)".format(len(made), args.step))
    return 0


def cmd_empties(args) -> int:
    need("ffmpeg")
    found = scanning.empty_stretches(Path(args.video).expanduser(), args.min)
    for a, b in found:
        say("{:7.2f}–{:7.2f}  {:4.1f} с".format(a, b, b - a))
    say("Всего: {}".format(len(found)))
    return 0


def cmd_texts(args) -> int:
    work = work_dir(args.work)
    out = Path(args.file).expanduser()
    n = scanning.screen_texts(work / "src" / "scenes", out)
    say("{} строк → {}".format(n, out))
    return 0


def cmd_frames(args) -> int:
    need("ffmpeg", "ffprobe")
    video = Path(args.video).expanduser()
    work = work_dir(args.work)
    if args.overview:
        out = Path(args.overview) if args.overview != "-" else work / "out" / "overview.jpg"
        step, per_row = sheets.overview(video, out)
        say("{}: шаг {:g} с, {} кадров в ряду, смотреть слева направо".format(out, step, per_row))
        return 0
    if not args.seconds:
        raise ToolError("Укажите секунды кадров или --overview для обзорного листа.")
    seconds = parse_secs(args.seconds, duration_of(video))
    label = args.label or video.stem
    for path in sheets.take_frames(video, work, label, seconds, sheets.parse_crop(args.crop), args.width):
        say("{}  → <WorkFrame name=\"{}\" />".format(path, path.stem))
    return 0


def cmd_sync(args) -> int:
    need("ffmpeg", "ffprobe")
    ok, _ = verify.sync_report(Path(args.base).expanduser(), Path(args.final).expanduser())
    say("Итог: " + ("речь на месте" if ok else "ВНЕ ДОПУСКА (сдвиг больше 10 мс или другая длительность)"))
    return 0 if ok else 1


def cmd_index(args) -> int:
    work = work_dir(args.work)
    ids = scaffold.write_index(work)
    say("Отрезки: " + ", ".join(ids))
    return 0


def cmd_example(args) -> int:
    work = work_dir(args.work)
    scaffold.use_example(work, args.force)
    scaffold.write_index(work)
    say("Образец положен в src/scenes/seg-a.tsx, src/data/layouts-a.ts и public/screens/.")
    return 0

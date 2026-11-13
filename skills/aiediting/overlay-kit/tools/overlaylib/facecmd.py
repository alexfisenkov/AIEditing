"""`face`: what the face track of a working folder holds, a safe rebuild of it, and a still right after every cut.

The speaker's frame must be on the new face from the first frame after a cut. This command is how that is watched: it lists
the cuts the track knows, names what in the folder still reads the track the earlier way, and renders the frames to look at.
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import List, Sequence

from . import face, facecuts, media, remotion, vmap
from .common import FPS, ToolError, say, warn, work_dir, write_atomic

READERS = ("src/kit/Presenter.tsx", "src/vertical/VPresenter.tsx")
AFTER = 0.2  # seconds after a cut at which the frame is looked at
BACKUP = "raw/face-before-rebuild.json"


FIX = {
    "src/vertical/VPresenter.tsx": "overlay.py vertical-init <папка> --renew (он заменяет файлы набора в src/vertical, кроме сцен c<N>.tsx "
                                   "и spans.json, и докладывает src/kit/faceTrack.ts и speakerBox.ts: свои правки файлов набора сначала сохраните)",
    "src/kit/Presenter.tsx": "сохраните свой src/kit/Presenter.tsx, скопируйте template/src/kit/Presenter.tsx, faceTrack.ts и speakerBox.ts "
                             "в src/kit/ и перенесите свои правки руками",
}


def _lacks(path: Path) -> List[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [what for marker, what in (("makeFace(", "сглаживает трек лица сам, сквозь склейки, и после склейки рамка отстаёт от лица"),
                                       ("useSpeakerBox(", "не сообщает рамку спикера проверке лица в рамке")) if marker not in text]


def stale_readers(work: Path) -> List[str]:
    """Presenters of the folder written by an earlier kit: they smooth the track through every cut themselves, or they do not
    report their window to the face check."""
    return [rel for rel in READERS if (work / rel).is_file() and _lacks(work / rel)]


def warn_stale(work: Path) -> None:
    for rel in stale_readers(work):
        warn("{} прежнего образца: {}. Обновить: {}.".format(rel, "; ".join(_lacks(work / rel)), FIX[rel]))


def _source(work: Path, rows: Sequence, given: str) -> Path:
    """The video a rebuild reads. A folder edited by markers needs the first accepted video; any other folder its own file."""
    own = work / "public" / "clips" / "source.mp4"
    if not rows:
        if given:
            raise ToolError("--video нужен только папке с картой времени. Здесь её нет: трек строится из public/clips/source.mp4.")
        return own
    if not given:
        raise ToolError("В папке карта времени (правки по маркерам): сцены читают трек лица в секундах первого принятого ролика, "
                        "а public/clips/source.mp4 уже другой. Передайте тот ролик: --video <файл> (16:9, 30 к/с; его рабочая копия "
                        "лежит в raw/rollback/clips/source.mp4, если правок по маркерам был один круг).")
    video = Path(given).expanduser()
    if own.is_file() and video.is_file() and (video.resolve() == own.resolve() or video.stat().st_size == own.stat().st_size):
        raise ToolError("--video — это и есть нынешний public/clips/source.mp4, ролик после правок. Нужен первый принятый: тот, который prepare "
                        "получил до правок по маркерам.")
    info = media.probe(video)
    media.check_16x9(info, need_sound=False)
    if abs(info["fps"] - FPS) > 0.01:
        raise ToolError("--video: {:.3f} к/с, а трек считает секунды по {} к/с. Возьмите рабочую копию того ролика (public/clips/source.mp4 "
                        "его папки) или приведите файл к {} к/с.".format(info["fps"], FPS, FPS))
    return video


def rebuild(work: Path, rows: Sequence, given: str) -> None:
    """A new track replaces the old one only when it was really built; the old one stays beside it."""
    video = _source(work, rows, given)
    if not video.is_file():
        raise ToolError("Нет файла: {}".format(video))
    old = face.load(work)
    track, note = face.detect(video)
    if track is None:
        raise ToolError("Трек не построен ({}). Прежний src/data/face.json оставлен как есть.".format(note))
    if rows:
        _check_first_video(track[-1][0], old, rows)
    target = work / "src" / "data" / "face.json"
    if target.is_file() and old != [face.CENTRE]:
        backup = _free_backup(work)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(target), str(backup))
        say("Прежний трек сохранён: {}".format(backup))
    write_atomic(target, json.dumps(track))
    say("Лицо: " + note)


def _check_first_video(end: float, old: Sequence, rows: Sequence) -> None:
    """The new track must cover the seconds of the scenes. The kept track is a witness only when it covers them itself:
    a track built by mistake from the video after the edits is shorter, and it is the very thing being mended."""
    reach = max(r[3] for r in rows)
    kept = "Прежний src/data/face.json оставлен как есть."
    if end + 1.0 < reach:
        raise ToolError("Это не первый принятый ролик: его трек кончается на {:.1f} с, а секунды сцен идут до {:.1f} с. {}".format(end, reach, kept))
    if old != [face.CENTRE] and old[-1][0] + 1.0 >= reach and abs(end - old[-1][0]) > 1.0:
        raise ToolError("Это другой ролик, не тот, с которого снят прежний трек: {:.1f} с против {:.1f} с. {}".format(end, old[-1][0], kept))


def _free_backup(work: Path) -> Path:
    """Every rebuild keeps the track it replaces: face-before-rebuild.json, then -2, -3 and so on."""
    first = work / BACKUP
    path, n = first, 1
    while path.exists():
        n += 1
        path = first.with_name("{}-{}{}".format(first.stem, n, first.suffix))
    return path


def joint_seconds(track: Sequence, rows: Sequence) -> List[float]:
    """Seconds of the file at which two rows of the time map meet and the face of the track is elsewhere after the joint."""
    last = len(track) - 1
    found = []
    for before, after in zip(rows, rows[1:]):
        left = track[max(0, min(last, math.ceil(before[3] / face.STEP) - 1))]
        right = track[max(0, min(last, math.ceil(after[2] / face.STEP)))]
        if facecuts.gap(left[1:4], right[1:4]) >= facecuts.JUMP:
            found.append(after[0])
    return found


def cut_seconds(track: Sequence, rows: Sequence) -> List[float]:
    """Seconds of the file at which the picture changes: every cut of the track that the file still holds, and every joint
    of an edit by markers across which the face jumps."""
    seen = []
    for scene in face.cuts_of(track):
        if rows and not any(r[2] <= scene < r[3] for r in rows):
            continue  # the cut lies in seconds an edit by markers removed
        seen.append(round(vmap.to_new(rows, scene), 4))
    seen += [round(second, 4) for second in joint_seconds(track, rows)]
    return sorted(set(seen))


def cut_frames(track: Sequence, rows: Sequence) -> List[float]:
    """Seconds of the file to look at: AFTER past every change of the picture."""
    return sorted({round(second + AFTER, 2) for second in cut_seconds(track, rows)})


def run_face(args) -> int:
    work = work_dir(args.work)
    rows = vmap.load_rows(work)
    if args.rebuild:
        rebuild(work, rows, args.video)
    elif args.video:
        raise ToolError("--video имеет смысл только вместе с --rebuild.")
    track = face.load(work)
    if track == [face.CENTRE]:
        say("Трека лица нет: рамка спикера держит центр кадра. Построить: overlay.py face <папка> --rebuild")
        if getattr(args, "check", False):
            raise ToolError("Лицо в рамке не проверено: трека лица нет.")
        return 0
    cuts = face.cuts_of(track)
    say("Трек лица: {} отсчётов, до {:.1f} с; смен кадра и склеек со скачком лица: {}".format(len(track), track[-1][0], len(cuts)))
    for scene in cuts:
        say("  {:9.2f} с сцены{}".format(scene, " → {:.2f} с файла".format(vmap.to_new(rows, scene)) if rows else ""))
    if face.is_old_kind(track):
        warn("трек прежнего образца (четыре числа в точке): сглажен сквозь смены кадра, своих склеек не знает. Пересобрать: "
             "overlay.py face <папка> --rebuild" + (" --video <первый принятый ролик>" if rows else ""))
    if rows:
        say("Правок по маркерам: {} кусков. На стыке кусков картинка тоже меняется: src/kit/faceTrack.ts режет трек и по ним. "
            "Стыков, через которые лицо в треке скачет: {}.".format(len(rows), len(joint_seconds(track, rows))))
    warn_stale(work)
    seconds = cut_frames(track, rows)
    if seconds:
        say("Кадры через {:g} с после каждой смены и каждого такого стыка (лицо целиком и по центру рамки): "
            "overlay.py face \"{}\" --frames".format(AFTER, work))
    if args.frames:
        remotion.ready(work)
        limit = remotion.duration(work)
        folder = work / "out" / "cuts"
        for stale in (sorted(folder.glob("*.jpg")) if folder.is_dir() else []):  # stills of cuts that may be gone by now
            stale.unlink()
        for second in seconds:
            if second >= limit:
                continue
            out = folder / "{:.2f}.jpg".format(second)
            remotion.still(work, "{:.2f}".format(second), out)
            say(str(out))
    if getattr(args, "check", False):
        remotion.ready(work)
        from . import facecheck  # facecheck reads the cuts from here

        found, unchecked = facecheck.check_long(work)
        if unchecked:
            raise ToolError("Лицо в рамке не проверено: {}.".format(unchecked))
        return 1 if found else 0
    return 0

"""Music and accent sounds only from the person's own folders; nothing is generated or downloaded.

params.music = "<folder>" | {"dir", "mood", "db": -20, "per_chapter": bool, "variants": int, "service", "tempo"}: tracks
from <folder>/<mood>/ first (or with the mood in the name), then the rest. `per_chapter`: every chapter its own track,
crossfaded (the whole video only); `variants`: that many beds in `музыка-варианты/`, the first one goes into the video.
No track: no bed and no error; when a service was chosen, `музыка-скачать.md` lists what to fetch, chapter by chapter.
params.sfx = "<folder>" | {"dir", "db"}: one accent under each card or chapter plate; {"roles": true | {"card": role,
"chapter": role}, "dir"?, "db"?}: the role's sound from a catalog (own folder first, then the kit's) starts `peak_ms`
early, so its peak lands on the plate. Both sit `db` below the voice.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
UNDER = -20.0
TO_FETCH = "музыка-скачать.md"
VARIANTS = "музыка-варианты"
MAX_VARIANTS = 5
FADE = 1.0  # the crossfade between the tracks of two chapters
ACCENT_ROLES = {"card": "pop", "chapter": "whoosh"}
SKILL = Path(__file__).resolve().parent.parent.parent
KIT_SFX = [SKILL / "overlay-kit" / "template" / "public" / "sfx", SKILL / "design" / "overlay-kit" / "template" / "public" / "sfx"]


def _spec(raw) -> Dict:
    if not raw:
        return {}
    return {"dir": raw} if isinstance(raw, str) else dict(raw)


def _tracks(folder: Path) -> List[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO)


def ordered(spec: Dict) -> List[Path]:
    """Every track of the folder, the mood's ones first."""
    folder = Path(spec.get("dir") or "").expanduser()
    if not spec.get("dir") or not folder.is_dir():
        return []
    mood, every = str(spec.get("mood") or "").lower(), _tracks(folder)
    first = (_tracks(folder / mood) if mood and (folder / mood).is_dir() else []) or [t for t in every if mood and mood in t.name.lower()]
    return first + [t for t in every if t not in first]


def pick(spec: Dict) -> Optional[Path]:
    found = ordered(spec)
    return found[0] if found else None


def _chapters_out(ctx) -> List[Tuple[float, str]]:
    """(second of the finished video, title) of every chapter that survived the cut."""
    from .speed import rate_of
    from .timeline import to_out

    rate = rate_of(ctx.p("speed", 1.0))
    found = [(to_out(float(c["start"]), ctx.keep), str(c.get("title") or "")) for c in ctx.chapters or []]
    return sorted((round(t / rate, 3), title) for t, title in found if t is not None)


def _length(ctx) -> float:
    from .speed import rate_of

    return sum(b - a for a, b in ctx.keep) / rate_of(ctx.p("speed", 1.0))


def _clock(t: float) -> str:
    t = int(round(t))
    return "{}:{:02d}:{:02d}".format(t // 3600, t % 3600 // 60, t % 60) if t >= 3600 else "{}:{:02d}".format(t // 60, t % 60)


def _to_fetch(ctx, spec: Dict) -> Path:
    """What to download from the chosen service: a row per chapter (or the whole video) with its length and mood."""
    total = _length(ctx)
    rows = _chapters_out(ctx) if spec.get("per_chapter") else []
    rows = rows or [(0.0, "весь ролик")]
    if rows[0][0] > 0.5:
        rows.insert(0, (0.0, "до первой главы"))
    mood, tempo = spec.get("mood") or "—", spec.get("tempo") or "—"
    lines = ["# Музыка: что скачать", "",
             "Сервис: {}. Папка для треков: {}.".format(spec.get("service"), spec.get("dir") or "не задана (params.music.dir)"),
             "Скачайте по треку на строку и положите в эту папку; следующий монтаж поставит их сам на 20 дБ тише голоса.", "",
             "| Глава | Начало | Длина | Настроение | Темп |", "|---|---|---|---|---|"]
    for k, (start, title) in enumerate(rows):
        end = rows[k + 1][0] if k + 1 < len(rows) else total
        lines.append("| {} | {} | {} | {} | {} |".format(title or "глава {}".format(k + 1), _clock(start), _clock(end - start), mood, tempo))
    path = Path(ctx.outdir) / TO_FETCH
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def _role_sounds(spec: Dict) -> Dict[str, Dict]:
    """kind (card|chapter) -> {file, peak_ms}: the role's first sound in the own folder's catalog, then the kit's."""
    wanted = dict(ACCENT_ROLES, **(spec["roles"] if isinstance(spec.get("roles"), dict) else {}))
    folders = ([Path(str(spec["dir"])).expanduser()] if spec.get("dir") else []) + KIT_SFX
    rows = []
    for folder in folders:
        try:
            rows += [(folder, r) for r in json.loads((folder / "catalog.json").read_text(encoding="utf-8")).get("sounds") or []]
        except (OSError, ValueError, AttributeError):
            continue
    out = {}
    for kind, role in wanted.items():
        hit = next(((f, r) for f, r in rows if r.get("role") == role and (f / str(r.get("file"))).is_file()), None)
        if hit:
            out[kind] = {"file": hit[0] / hit[1]["file"], "peak_ms": int(hit[1].get("peak_ms") or 0)}
    return out


def plan_music(ctx) -> None:
    spec = _spec(ctx.p("music"))
    tracks = ordered(spec) if spec else []
    if not tracks:
        ctx.note("Без музыки: {} — музыка берётся только из вашей папки (params.music)".format(
            "папка не задана" if not spec.get("dir") else "в папке {} нет треков".format(spec.get("dir"))))
        if spec.get("service"):
            ctx.note("Что скачать из {}: {}".format(spec["service"], _to_fetch(ctx, spec)))
    else:
        ctx.music = {"track": tracks[0], "db": float(spec.get("db", UNDER))}
        variants = max(1, min(int(spec.get("variants") or 1), MAX_VARIANTS))
        chapters = [t for t, _ in _chapters_out(ctx) if t > 0.5] if spec.get("per_chapter") and ctx.pieces is None else []
        if variants > 1 or chapters:
            ctx.music.update(tracks=tracks, chapters=chapters, variants=variants, outdir=Path(ctx.outdir))
    sfx = _spec(ctx.p("sfx"))
    if sfx.get("roles"):
        found = _role_sounds(sfx)
        if found:
            ctx.music.update(accent_roles=found, accent_db=float(sfx.get("db", UNDER)), chapter_at=[t for t, _ in _chapters_out(ctx)])
        else:
            ctx.note("Звуков по ролям нет: у своей папки нет каталога (overlay.py sfxcat <папка>), набора графики рядом тоже нет")
        return
    accent = pick(sfx) if sfx else None
    if accent is not None:
        ctx.music.update(accent=accent, accent_db=float(sfx.get("db", UNDER)))


def _bed(music: Dict, variant: int, dur: float, lufs: float, out: Path) -> Path:
    """One bed: the chapters' tracks, each levelled `db` under the voice, crossfaded, faded out at the end."""
    from ..media.ffmpeg import run

    tracks, bounds = music["tracks"], [0.0] + [t for t in music.get("chapters") or [] if 0.5 < t < dur - 0.5] + [dur]
    inputs, parts = [], []
    for k in range(len(bounds) - 1):
        last = k == len(bounds) - 2
        a, length = bounds[k], bounds[k + 1] - bounds[k] + (0.0 if last else FADE)
        inputs += ["-stream_loop", "-1", "-i", tracks[(k + variant) % len(tracks)]]
        parts.append("[{k}:a]atrim=0:{n:.3f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
                     "loudnorm=I={i:.1f},afade=t=in:st=0:d={fi},afade=t=out:st={fo:.3f}:d={fd},adelay={ms}|{ms}[s{k}]".format(
                         k=k, n=length, i=lufs + music["db"], fi=FADE if k else 0.01, fo=max(0.0, length - (1.5 if last else FADE)),
                         fd=1.5 if last else FADE, ms=int(a * 1000)))
    n = len(bounds) - 1
    parts.append("{}amix=inputs={}:duration=longest:normalize=0,atrim=0:{:.3f}[bed]".format(
        "".join("[s{}]".format(k) for k in range(n)), n, dur))
    out.parent.mkdir(parents=True, exist_ok=True)
    run(inputs + ["-filter_complex", ";".join(parts), "-map", "[bed]", "-c:a", "aac", "-b:a", "192k", out])
    return out


def mix(video: Path, music: Dict, accents: List[float], lufs: float, out: Path) -> Path:
    """Voice as is; the bed looped, levelled `db` under the voice and faded out; accents at their times."""
    from ..media import probe
    from ..media.ffmpeg import run

    dur = probe(video)["duration"]
    inputs, parts, pads = ["-i", video], [], ["[0:a]"]
    if music.get("tracks"):
        folder, place = Path(music["outdir"]) / VARIANTS, Path(out).parent  # a 9:16 clip renders in a run folder of its id
        prefix = place.name + "-" if place.parent.name == ".aiediting-run" and place.name != "whole" else ""
        beds = [_bed(music, v, dur, lufs, folder / "{}вариант-{}.m4a".format(prefix, v + 1)) for v in range(music.get("variants") or 1)]
        inputs += ["-i", beds[0]]
        pads.append("[1:a]")
    elif music.get("track"):
        inputs += ["-stream_loop", "-1", "-i", music["track"]]
        parts.append("[1:a]atrim=0:{d:.3f},loudnorm=I={i:.1f},afade=t=out:st={f:.3f}:d=1.5[bed]".format(
            d=dur, i=lufs + music["db"], f=max(0.0, dur - 1.5)))
        pads.append("[bed]")
    roles = music.get("accent_roles") or {}
    for k, t in enumerate(accents if music.get("accent") or roles else []):
        if roles:
            kind = "chapter" if any(abs(t - c) < 0.05 for c in music.get("chapter_at") or []) else "card"
            sound = roles.get(kind) or roles.get("card") or roles.get("chapter")
            file, t = sound["file"], max(0.0, t - sound["peak_ms"] / 1000.0)
        else:
            file = music["accent"]
        idx = sum(1 for x in inputs if x == "-i")  # a looped bed takes four words, not two
        inputs += ["-i", file]
        parts.append("[{i}:a]volume={db}dB,adelay={ms}|{ms}[s{k}]".format(i=idx, db=music["accent_db"], ms=int(round(t * 1000)), k=k))
        pads.append("[s{}]".format(k))
    if len(pads) == 1:
        return video
    parts.append("{}amix=inputs={}:duration=first:normalize=0[aout]".format("".join(pads), len(pads)))
    run(inputs + ["-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[aout]", "-c:v", "copy",
                  "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    return out

"""Music and accent sounds only from the person's own library folder; nothing is generated or downloaded.

params.music = "<folder>" | {"dir", "mood", "db": -20}: a track is picked from <folder>/<mood>/ (or any
track whose name has the mood), else the first track. params.sfx = "<folder>" | {"dir", "db"}: one
accent under each card or chapter plate. Both sit `db` below the voice.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
UNDER = -20.0


def _spec(raw) -> Dict:
    if not raw:
        return {}
    return {"dir": raw} if isinstance(raw, str) else dict(raw)


def _tracks(folder: Path) -> List[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO)


def pick(spec: Dict) -> Optional[Path]:
    folder = Path(spec.get("dir", "")).expanduser()
    if not folder.is_dir():
        return None
    mood = str(spec.get("mood") or "").lower()
    if mood and (folder / mood).is_dir() and _tracks(folder / mood):
        return _tracks(folder / mood)[0]
    every = _tracks(folder)
    return next((t for t in every if mood and mood in t.name.lower()), every[0] if every else None)


def plan_music(ctx) -> None:
    spec = _spec(ctx.p("music"))
    track = pick(spec) if spec else None
    if track is None:
        ctx.note("Без музыки: {} — музыка берётся только из вашей папки-библиотеки (params.music)".format(
            "папка-библиотека не задана" if not spec else "в папке {} нет треков".format(spec.get("dir"))))
    else:
        ctx.music = {"track": track, "db": float(spec.get("db", UNDER))}
    sfx = _spec(ctx.p("sfx"))
    accent = pick(sfx) if sfx else None
    if accent is not None:
        ctx.music.update(accent=accent, accent_db=float(sfx.get("db", UNDER)))


def mix(video: Path, music: Dict, accents: List[float], lufs: float, out: Path) -> Path:
    """Voice as is; the bed looped, levelled `db` under the voice and faded out; accents at their times."""
    from ..media import probe
    from ..media.ffmpeg import run

    dur = probe(video)["duration"]
    inputs, parts, pads = ["-i", video], [], ["[0:a]"]
    if music.get("track"):
        inputs += ["-stream_loop", "-1", "-i", music["track"]]
        parts.append("[1:a]atrim=0:{d:.3f},loudnorm=I={i:.1f},afade=t=out:st={f:.3f}:d=1.5[bed]".format(
            d=dur, i=lufs + music["db"], f=max(0.0, dur - 1.5)))
        pads.append("[bed]")
    for k, t in enumerate(accents if music.get("accent") else []):
        idx = len(inputs) // 2
        inputs += ["-i", music["accent"]]
        parts.append("[{i}:a]volume={db}dB,adelay={ms}|{ms}[s{k}]".format(
            i=idx, db=music["accent_db"], ms=int(t * 1000), k=k))
        pads.append("[s{}]".format(k))
    if len(pads) == 1:
        return video
    parts.append("{}amix=inputs={}:duration=first:normalize=0[aout]".format("".join(pads), len(pads)))
    run(inputs + ["-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[aout]", "-c:v", "copy",
                  "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    return out

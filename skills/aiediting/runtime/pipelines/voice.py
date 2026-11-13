"""Step voice_clean: the voice cleaned in Auphonic replaces the sound before any cut; the original sound stays beside.

params.voice = {"service": "auphonic", "preset": "мягко" | "средне" | "сильно" | <Auphonic preset id or name> | {algorithms},
"key_env"?: "AUPHONIC_API_KEY"}. The preset is chosen by ear once (`ae.py voice-try`). Everything lives in `.звук/` of the
issue folder: `исходный.wav` (the original sound), `чистый.wav` and the source with the clean sound under its own name.
A second run with the same source and preset pays nothing: the clean sound is reused. With a sound recorded apart
(`--audio`) and the step `angles`, that sound is the one cleaned: `angles` puts its clean voice under the picture.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Union

SOUND = ".звук"
ORIGINAL = "исходный.wav"
CLEAN = "чистый.wav"
STAMP = "чистый.json"
DEFAULT = "средне"
# heard side by side in voice-try; Auphonic's algorithms (its JSON API names)
PRESETS: Dict[str, Dict] = {
    "мягко": {"denoise": True, "denoisemethod": "dynamic", "denoiseamount": 6, "leveler": True,
              "normloudness": True, "loudnesstarget": -16, "filtering": True, "filtermethod": "hipfilter"},
    "средне": {"denoise": True, "denoisemethod": "dynamic", "denoiseamount": 12, "leveler": True,
               "normloudness": True, "loudnesstarget": -16, "filtering": True, "filtermethod": "autoeq"},
    "сильно": {"denoise": True, "denoisemethod": "speech_isolation", "leveler": True,
               "normloudness": True, "loudnesstarget": -16, "filtering": True, "filtermethod": "autoeq"},
}
_AUDIO = {".mp4": ["-c:a", "aac", "-b:a", "320k"], ".m4v": ["-c:a", "aac", "-b:a", "320k"], ".webm": ["-c:a", "libopus"]}


def spec_of(raw) -> Dict:
    if not raw:
        return {}
    return {"service": "auphonic", "preset": raw} if isinstance(raw, str) else dict(raw)


def preset_of(spec: Dict) -> Union[str, Dict]:
    """A preset word of ours becomes its algorithms; anything else is the person's own Auphonic preset."""
    chosen = spec.get("preset") or DEFAULT
    return dict(PRESETS[chosen]) if isinstance(chosen, str) and chosen in PRESETS else chosen


def extract(src: Path, out: Path) -> Path:
    """The first sound track of `src` as it is (rate, channels), 16-bit WAV."""
    from ..media.ffmpeg import run

    out.parent.mkdir(parents=True, exist_ok=True)
    run(["-i", src, "-map", "0:a:0", "-vn", "-c:a", "pcm_s16le", out])
    return out


def mux(video: Path, audio: Path, out: Path) -> Path:
    """The picture of `video` untouched with `audio` as its only sound, as long as the picture."""
    from ..media.ffmpeg import run

    codec = _AUDIO.get(Path(out).suffix.lower(), ["-c:a", "pcm_s16le"])
    run(["-i", video, "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy"] + codec +
        ["-af", "apad", "-shortest", out])
    return out


def _stamp(src: Path, preset) -> str:
    st = src.stat()
    raw = json.dumps([src.name, st.st_size, int(st.st_mtime), preset], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _known(folder: Path, src: Path, preset) -> bool:
    """`.звук/чистый.wav` is the sound of this very `src` cleaned with this preset."""
    try:
        known = json.loads((folder / STAMP).read_text(encoding="utf-8")).get("stamp")
    except (OSError, ValueError, AttributeError):
        known = None
    return known == _stamp(src, preset) and (folder / CLEAN).is_file()


def clean_of(ctx, sound: Path) -> Path:
    """The cleaned voice of `sound` when this run's `voice_clean` made it, else `sound` itself. Files are lined up by
    `sound` as recorded: the clean voice keeps its timing, not always the rhythm of the room."""
    spec = spec_of(ctx.p("voice"))
    folder = Path(ctx.outdir) / SOUND
    if ctx.has("voice_clean") and spec and _known(folder, Path(sound), preset_of(spec)):
        return (folder / CLEAN).resolve()
    return sound


def _cleaned(folder: Path, src: Path, preset, spec: Dict) -> bool:
    """`.звук/чистый.wav` from the sound of `src`, paid once per file and preset; True when it was made now."""
    from ..services import auphonic

    if _known(folder, src, preset):
        return False
    extract(src, folder / ORIGINAL)
    auphonic.process(folder / ORIGINAL, preset, folder / CLEAN, spec.get("key_env") or auphonic.KEY_ENV)
    (folder / STAMP).write_text(json.dumps({"stamp": _stamp(src, preset), "preset": preset}, ensure_ascii=False),
                                encoding="utf-8")
    return True


def plan_voice(ctx) -> None:
    from ..media import probe

    spec = spec_of(ctx.p("voice"))
    if not spec:
        ctx.note("Шаг voice_clean выбран, но params.voice не задан — голос не чистился")
        return
    if spec.get("service", "auphonic") != "auphonic":
        ctx.note("Чистка голоса: сервис {} не поддерживается, есть только auphonic — голос не чистился".format(spec.get("service")))
        return
    apart = ctx.audio_src is not None and ctx.has("angles")  # the video's sound is the recorder's, not the camera's
    src = Path(ctx.audio_src if apart else ctx.src)
    if not (probe(src) if apart else ctx.info).get("has_audio"):
        ctx.note("Чистка голоса: в {} нет звука".format("отдельном звуке" if apart else "исходнике"))
        return
    folder, preset = Path(ctx.outdir) / SOUND, preset_of(spec)
    muxed = folder / src.name
    if _cleaned(folder, src, preset, spec) and muxed.exists():
        muxed.unlink()
    name = spec.get("preset") or DEFAULT if not isinstance(spec.get("preset"), dict) else "свой"
    if apart:  # `angles` lines the recorder up as it was recorded and takes its clean voice (clean_of)
        ctx.note("Голос очищен в Auphonic (пресет {}) в отдельном звуке {}; исходный — {}/{}".format(name, src.name, SOUND, ORIGINAL))
        return
    if not muxed.is_file():
        mux(src, folder / CLEAN, muxed)
    ctx.src, ctx.info = muxed.resolve(), probe(muxed)
    ctx.note("Голос очищен в Auphonic (пресет {}); исходный звук — {}/{}".format(name, SOUND, ORIGINAL))

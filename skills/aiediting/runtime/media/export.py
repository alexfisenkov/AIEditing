"""Copies of a finished 9:16 video for Reels, Shorts and TikTok: 1080x1920, H.264/AAC, platform loudness.

Safe zones are shares of the frame the platform's own buttons and captions cover — approximate, from
the platforms' creator guidance; text is placed inside the shared zone (`safe_zone`) of all three.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .codec import encode
from .ffmpeg import ensure_file, run
from .loudness import RANGE, _measure
from .probe import probe
from .vertical import BACKGROUND, SIZE

PLATFORMS: Dict[str, Dict] = {
    "reels": {"title": "Instagram Reels", "lufs": -14.0, "true_peak": -1.0,
              "safe": {"top": 0.14, "bottom": 0.35, "left": 0.06, "right": 0.06}},
    "shorts": {"title": "YouTube Shorts", "lufs": -14.0, "true_peak": -1.0,
               "safe": {"top": 0.08, "bottom": 0.25, "left": 0.06, "right": 0.13}},
    "tiktok": {"title": "TikTok", "lufs": -14.0, "true_peak": -1.0,
               "safe": {"top": 0.08, "bottom": 0.25, "left": 0.06, "right": 0.13}},
}


def safe_zone(names=None) -> Dict[str, float]:
    """The zone clear of every named platform's buttons: {"top","bottom","side"} as shares."""
    chosen = [PLATFORMS[n]["safe"] for n in (names or PLATFORMS)]
    return {"top": max(s["top"] for s in chosen), "bottom": max(s["bottom"] for s in chosen),
            "side": max(max(s["left"], s["right"]) for s in chosen)}


def _audio_filter(src, lufs: float, peak: float) -> str:
    m = _measure(src, lufs)
    return ("loudnorm=I={i}:TP={tp}:LRA={lra}:measured_I={mi}:measured_TP={mtp}:measured_LRA={mlra}:"
            "measured_thresh={mth}:offset={off}:linear=true").format(
        i=lufs, tp=peak, lra=RANGE, mi=m["input_i"], mtp=m["input_tp"], mlra=m["input_lra"],
        mth=m["input_thresh"], off=m["target_offset"])


def _one(src: Path, info: Dict, spec: Dict, out: Path) -> Path:
    audio = (["-af", _audio_filter(src, spec["lufs"], spec["true_peak"]), "-ar", "48000",
              "-c:a", "aac", "-b:a", "192k"] if info["has_audio"] else [])
    tail = ["-map", "0:v:0"] + (["-map", "0:a:0"] if info["has_audio"] else []) + audio
    tail += ["-movflags", "+faststart"]
    fits = (info["width"], info["height"]) == SIZE and info["rotation"] == 0 and info["fps"] <= 60
    if fits:  # already right: the picture is copied, only the sound is levelled
        run(["-i", src, "-c:v", "copy"] + tail + [out])
        return out
    vf = ("scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={bg},"
          "setsar=1,fps=fps='min(source_fps,60)'").format(w=SIZE[0], h=SIZE[1], bg=BACKGROUND)
    encode(["-i", src, "-vf", vf], tail, out, kbps=8000)
    return out


def export_platforms(src, outdir, platforms: Optional[List[str]] = None) -> List[Path]:
    """Writes `<name>-reels.mp4`, `<name>-shorts.mp4`, `<name>-tiktok.mp4` into `outdir`."""
    src, outdir = ensure_file(src), Path(outdir)
    info = probe(src)
    outdir.mkdir(parents=True, exist_ok=True)
    return [_one(src, info, PLATFORMS[name], outdir / "{}-{}.mp4".format(src.stem, name))
            for name in (platforms or list(PLATFORMS))]

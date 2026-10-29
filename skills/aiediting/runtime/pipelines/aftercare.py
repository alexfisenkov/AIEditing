"""After the video is made: sidecar .srt, platform copies, sync check, second listening."""
from __future__ import annotations

from pathlib import Path
from typing import Dict


def fit_audio(path: Path, out: Path) -> Path:
    """Levelling resamples the sound and can leave it a little longer than the picture: trim the tail."""
    from ..media.drift import _stream_bounds
    from ..media.ffmpeg import run

    video, audio = _stream_bounds(path, "v:0"), _stream_bounds(path, "a:0")
    if video is None or audio is None or audio[1] <= video[1] + 0.02:
        return path
    run(["-i", path, "-map", "0", "-c", "copy", "-t", "{:.3f}".format(video[1]), "-movflags", "+faststart", out])
    return out


def after(ctx, piece: Dict, final: Path, done: Dict) -> Dict:
    from .. import media

    if ctx.has("write_srt"):
        from .subtitles import write_piece_srt

        srt = write_piece_srt(ctx, piece["keep"], final.with_suffix(".srt"))
        done["srt"] = srt["path"]
        ctx.report["fixes"] += srt["fixes"]
    if ctx.has("export_platforms"):
        done["exports"] = media.export_platforms(final, ctx.outdir)
        ctx.report["exports"] += done["exports"]
    done["drift_ms"] = media.drift_ms(final)
    ctx.report["drift_ms"] = max(ctx.report["drift_ms"], done["drift_ms"])
    if ctx.has("verify_words"):
        from .verify import check_words

        done["words_lost"] = check_words(ctx, final, piece["keep"])
        ctx.report["words_lost"] += done["words_lost"]
    return done

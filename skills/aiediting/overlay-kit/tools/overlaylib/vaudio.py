"""Looking at the sound of a finished clip: the quiet places between words, a hum in them, the silence of the tail (needs numpy).

A hum is what the person heard in a clip that carried a music pad: the quiet places were only 11.8 dB below the speech, in
clean speech they are about 20 dB below. So two signs are measured: how far below the speech the quiet places lie, and whether
the quiet places hold a lasting tone between 60 and 250 Hz.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from .audiosync import _np
from .common import ToolError

SR = 8000
WINDOW = 0.05  # seconds of one level reading
MIN_GAP_DB = 16.0  # the quiet places must lie at least this far below the speech
TONE_DB = 10.0  # a tone this much above its neighbours in 60-250 Hz is a hum
BAND = (60.0, 250.0)
FFT = 1024
FLOOR_DB = -80.0  # windows below this are digital silence, not a quiet place of the room
QUIET_MARGIN_DB = 6.0  # a window within this of the quietest tenth is a quiet place
MIN_FRAMES = 6  # quiet material needed for the tone test (FFT-long pieces)


def decode(path: Path, sr: int = SR):
    """Mono float samples of the first audio stream at `sr`."""
    np = _np()
    done = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if done.returncode != 0 or not done.stdout:
        raise ToolError("Не читается звук файла {}: {}".format(path, done.stderr.decode("utf-8", "replace").strip()[-200:]))
    return np.frombuffer(done.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def levels(x, sr: int = SR, win: float = WINDOW):
    """dBFS of consecutive windows."""
    np = _np()
    n = int(sr * win)
    count = len(x) // n
    if count == 0:
        return np.zeros(0)
    body = x[: count * n].reshape(count, n)
    rms = np.sqrt(np.mean(body * body, axis=1))
    return 20 * np.log10(np.maximum(rms, 1e-9))


def hum_report(x, speech_end: float, sr: int = SR) -> Dict:
    """{'gap_db', 'speech_db', 'quiet_db', 'tone_hz', 'tone_db', 'problems': [...]} over the speech part [0, speech_end]."""
    np = _np()
    part = x[: int(speech_end * sr)]
    lv = levels(part, sr)
    live = lv[lv > FLOOR_DB]
    report: Dict = {"gap_db": None, "speech_db": None, "quiet_db": None, "tone_hz": None, "tone_db": None, "problems": []}
    if len(live) < 20:
        report["problems"].append("в речи слишком мало звука, чтобы судить о гуле")
        return report
    speech_db, quiet_db = float(np.percentile(live, 90)), float(np.percentile(live, 10))
    report.update(speech_db=speech_db, quiet_db=quiet_db, gap_db=speech_db - quiet_db)
    if report["gap_db"] < MIN_GAP_DB:
        report["problems"].append("тихие места лишь на {:.1f} дБ ниже речи (чистая речь: около 20 дБ, нужно не меньше {:g}): под речью что-то лежит".format(report["gap_db"], MIN_GAP_DB))
    hz, tone = tonal_peak(part, lv, quiet_db + QUIET_MARGIN_DB, sr)
    report.update(tone_hz=hz, tone_db=tone)
    if hz is not None and tone is not None and tone >= TONE_DB:
        report["problems"].append("в тихих местах стоит тон {:.0f} Гц, он выше соседних частот на {:.0f} дБ: это гул".format(hz, tone))
    return report


def tonal_peak(x, lv, quiet_level: float, sr: int = SR, win: float = WINDOW):
    """(Hz, dB above the band's median) of the strongest tone in 60-250 Hz over the quiet windows; (None, None) when too few."""
    np = _np()
    step = int(sr * win)
    quiet = np.zeros(len(lv) * step, dtype=bool)
    for i, level in enumerate(lv):
        if level <= quiet_level:
            quiet[i * step:(i + 1) * step] = True
    spectra = []
    i = 0
    while i + FFT <= len(quiet):  # FFT-long pieces that lie wholly in quiet places
        if quiet[i:i + FFT].all():
            piece = x[i:i + FFT] * np.hanning(FFT)
            spectra.append(np.abs(np.fft.rfft(piece)) ** 2)
            i += FFT // 2
        else:
            i += step
    if len(spectra) < MIN_FRAMES:
        return None, None
    power = np.mean(spectra, axis=0)
    freq = np.fft.rfftfreq(FFT, 1.0 / sr)
    sel = (freq >= BAND[0]) & (freq <= BAND[1])
    band, hz = power[sel], freq[sel]
    base = float(np.median(band))
    if base <= 0:
        return None, None
    k = int(np.argmax(band))
    return float(hz[k]), float(10 * np.log10(band[k] / base))


def tail_peak_db(x, from_second: float, sr: int = SR) -> Optional[float]:
    """Loudest sample (dBFS) after `from_second`; None when there is nothing after it."""
    np = _np()
    tail = x[int(from_second * sr):]
    if len(tail) == 0:
        return None
    return float(20 * np.log10(max(float(np.max(np.abs(tail))), 1e-9)))

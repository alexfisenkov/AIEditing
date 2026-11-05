"""`final`: full render, delay of the AAC measured and removed, loudness set, atomic write, sync check."""
from __future__ import annotations

import os
from pathlib import Path

from . import audiosync, loudness, remotion, verify
from .common import ToolError, ffmpeg, say, warn, work_dir
from .media import duration_of

MAX_SHIFT = 0.25  # a larger measured delay is a mismatch, not an encoder delay: do not "correct" it
REPORT, PENDING, READY = "отчёт.md", "Графика ещё не наложена", "## Готовое"
# Primaries and transfer only, and no pixel changes: older Remotion leaves them empty even with --color-space=bt709. Range and matrix
# are what the pixels really are, so they are not written here: a wrong render is refused by verify.color_problems, not relabelled.
COLOR_TAGS = "h264_metadata=colour_primaries=1:transfer_characteristics=1"


def measure_shift(render: Path, speech: Path) -> float:
    """Seconds the render's audio runs late against the speech it was built from (median of windows)."""
    lags = audiosync.measure(audiosync.pcm(speech), audiosync.pcm(render))
    if not lags:
        warn("в звуке нет участков с речью: сдвиг AAC не измерен и не убран.")
        return 0.0
    shift = audiosync.median([lag for _, lag in lags])
    if abs(shift) > MAX_SHIFT:
        warn("измеренный сдвиг {:.0f} мс слишком велик для задержки кодера: он не убран, проверьте рендер.".format(shift * 1000))
        return 0.0
    return shift


def mix(render: Path, out: Path, audio_filter: str, length: float) -> None:
    """The picture as it is, the sound levelled. ffmpeg 9's loudnorm flushes a tenth of a second more than it was given: the
    result lasts as long as the picture, or `sync` refuses it for its length."""
    ffmpeg("-i", render, "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-bsf:v", COLOR_TAGS, "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-af", audio_filter, "-t", "{:.3f}".format(length), "-movflags", "+faststart", out, what="Сведение звука")


def run_final(args) -> int:
    work = work_dir(args.work)
    release = Path(args.release).expanduser()
    name = args.name if args.name.lower().endswith(".mp4") else args.name + ".mp4"
    if Path(name).name != name:
        raise ToolError("Имя файла должно быть именем, а не путём: {}".format(name))
    remotion.ready(work)
    audiosync._np()  # its absence is said before a long render, not after it
    remotion.typecheck(work)
    render = work / "out" / "render.mp4"
    if args.reuse_render and render.is_file():
        say("Беру готовый рендер: " + str(render))
    else:
        remotion.render(work, render, draft=False)
    speech = work / "public" / "clips" / "speech.wav"
    shift = measure_shift(render, speech)
    say("Сдвиг звука рендера: {:+.1f} мс (убирается)".format(shift * 1000))
    measured = loudness.measure(render, args.lufs)
    say("Громкость рендера до сведения: {} LUFS, пик {} dBFS".format(measured["input_i"], measured["input_tp"]))
    release.mkdir(parents=True, exist_ok=True)
    tmp = release / (".{}.part.mp4".format(Path(name).stem))
    mix(render, tmp, loudness.audio_filter(args.lufs, measured, shift), remotion.duration(work))
    final = release / name
    say("Итог: {} ({:.2f} с, {:.1f} МБ)".format(final, duration_of(tmp), tmp.stat().st_size / 1e6))
    say(loudness.summary(tmp))
    ok, worst = verify.sync_report(speech, tmp, length=remotion.duration(work))
    say("Сверка звука: " + ("в допуске" if ok else "ВНЕ ДОПУСКА"))
    color = verify.color_problems(tmp)
    if color:
        ok = False
        say("Цвет не для доставки: {}. Рендер старой версии: сделайте final без --reuse-render".format("; ".join(color)))
    if not ok:  # an earlier good file stays under the final name
        say("Файл не выпущен, он лежит как {}".format(tmp))
        return 1
    os.replace(str(tmp), str(final))
    mark_report(release, name)
    return 0


def mark_report(release: Path, name: str) -> None:
    """The pipeline's report said the graphics were still to come: now they are there, and the file to watch is named."""
    report = release / REPORT
    if not report.is_file():
        return
    lines = report.read_text(encoding="utf-8").splitlines()
    lines = ["- Графика наложена: {}".format(name) if PENDING in line else line for line in lines]
    row = "- {} — готовый ролик с графикой".format(name)
    if READY in lines and row not in lines:
        lines.insert(lines.index(READY) + 2, row)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

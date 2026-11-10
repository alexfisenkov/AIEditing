"""Read-only scene, audio-feature and two-recorder offset measurements.

Every audio decode is a bounded window. The sync result describes alignment only;
no media is cut, shifted, stretched or rendered by this module.
"""
from __future__ import annotations

import math
from pathlib import Path

from .common import RecipeError, extract_mono_audio, probe, require_input, write_json

RATE = 8000
MAX_WINDOW = 60.0
MAX_LAG = 10.0
QUIET_RMS = 0.01  # -40 dBFS, a diagnostic threshold rather than a speech classifier.


def _store(opt, result):
    path = getattr(opt, "output", None)
    if path:
        target = Path(path).expanduser().resolve()
        if target.suffix.lower() != ".json":
            raise RecipeError("--output must name a .json report file")
        for key in ("source", "reference", "target"):
            if result.get(key) and target == Path(result[key]).resolve():
                raise RecipeError("Report path must differ from every media source")
        result["report_file"] = str(write_json(path, result, replace=bool(getattr(opt, "replace", False))))
    return result


def scenes(opt) -> dict:
    """Source-time shot boundaries; a cut is never a claim about the best take."""
    from scenedetect import AdaptiveDetector, ContentDetector, detect

    source = require_input(opt.source)
    info = probe(source)
    if not info["has_video"] or info["duration"] <= 0:
        raise RecipeError("Для поиска сцен нужен видеоряд с длительностью")
    start = float(opt.start)
    end = float(opt.end) if opt.end is not None else float(info["duration"])
    if start < 0 or end <= start or end > info["duration"] + 0.1:
        raise RecipeError("Интервал сцен должен лежать внутри исходного видео")
    if not 0 < opt.min_scene <= 3600:
        raise RecipeError("--min-scene задаётся положительным числом секунд")
    threshold = float(opt.threshold) if opt.threshold is not None else (27.0 if opt.detector == "content" else 3.0)
    if threshold <= 0:
        raise RecipeError("--threshold должен быть положительным")
    min_length = "{:.6f}s".format(opt.min_scene)
    detector = (ContentDetector(threshold=threshold, min_scene_len=min_length) if opt.detector == "content"
                else AdaptiveDetector(adaptive_threshold=threshold, min_scene_len=min_length))
    found = detect(str(source), detector, start_time="{:.6f}s".format(start), end_time="{:.6f}s".format(end))
    listed = [{"start_seconds": round(float(a.seconds), 6), "end_seconds": round(float(b.seconds), 6),
               "start_frame": int(a.frame_num), "end_frame": int(b.frame_num)} for a, b in found]
    if not listed:
        fps = float(info["fps"] or 0)
        listed = [{"start_seconds": round(start, 6), "end_seconds": round(end, 6),
                   "start_frame": round(start * fps), "end_frame": round(end * fps)}]
    result = {"kind": "scenes", "source": str(source), "fps": float(info["fps"] or 0),
              "detector": opt.detector, "threshold": threshold, "min_scene_seconds": opt.min_scene,
              "analyzed_start_seconds": start, "analyzed_end_seconds": end,
              "cuts_seconds": [s["start_seconds"] for s in listed[1:]], "scenes": listed,
              "note": "Границы смены плана; не оценка качества дублей или содержания речи."}
    return _store(opt, result)


def _audio_window(source, at, window, info):
    if not info["has_audio"]:
        raise RecipeError("В исходнике нет аудиодорожки")
    if at < 0 or window <= 0 or window > MAX_WINDOW or at >= info["duration"]:
        raise RecipeError("Нужен интервал звука внутри файла; --window: (0, {}] с".format(MAX_WINDOW))
    duration = min(window, max(0.0, info["duration"] - at))
    samples = extract_mono_audio(source, at, duration, RATE)
    if len(samples) < int(RATE * min(duration, 0.2)):
        raise RecipeError("Аудио в выбранном интервале слишком короткое")
    return samples


def audio_report(opt) -> dict:
    """Peak/RMS/quiet fraction and transients for one bounded portion, not LUFS."""
    import librosa
    import numpy as np

    source = require_input(opt.source)
    info = probe(source)
    samples = _audio_window(source, float(opt.at), float(opt.window), info)
    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    frames = librosa.feature.rms(y=samples, frame_length=400, hop_length=160, center=False)[0]
    if frames.size == 0:
        raise RecipeError("Аудио слишком короткое для анализа")
    quiet = float(np.mean(frames < QUIET_RMS))
    # Onsets are transients, not words. Include at most 100 to keep a report bounded.
    onset_times = librosa.onset.onset_detect(y=samples, sr=RATE, units="time", hop_length=160)
    result = {"kind": "audio-report", "source": str(source), "sample_rate": RATE,
              "analyzed_start_seconds": float(opt.at), "analyzed_seconds": round(len(samples) / RATE, 6),
              "peak_dbfs": round(20 * math.log10(max(peak, 1e-12)), 2),
              "rms_dbfs": round(20 * math.log10(max(rms, 1e-12)), 2),
              "crest_db": round(20 * math.log10(max(peak, 1e-12) / max(rms, 1e-12)), 2),
              "quiet_fraction": round(quiet, 4), "quiet_threshold_dbfs": -40.0,
              "transient_count": int(len(onset_times)),
              "transient_seconds": [round(float(opt.at) + float(t), 3) for t in onset_times[:100]],
              "note": "dBFS и транзиенты в выбранном окне; это не LUFS, не распознавание речи и не оценка качества."}
    return _store(opt, result)


def _match(reference, target, reference_at, search_at):
    """Find where one bounded reference window begins on a bounded target search window."""
    import numpy as np
    from scipy.signal import correlate

    if len(reference) < RATE or len(target) < len(reference):
        raise RecipeError("Для синхронизации нужен перекрывающийся звук не короче секунды")
    ref = np.asarray(reference, dtype=np.float64)
    look = np.asarray(target, dtype=np.float64)
    ref -= ref.mean()
    look -= look.mean()
    ref_energy = float(np.dot(ref, ref))
    if ref_energy / len(ref) < 1e-6 or float(np.dot(look, look)) / len(look) < 1e-6:
        raise RecipeError("В выбранном окне тишина или слишком тихий звук")
    dots = correlate(look, ref, mode="valid", method="fft")
    squared = np.concatenate(([0.0], np.cumsum(look * look)))
    energy = np.maximum(squared[len(ref):] - squared[:-len(ref)], 1e-12)
    score = dots / np.sqrt(ref_energy * energy)
    best = int(np.argmax(score))
    peak = float(score[best])
    if not math.isfinite(peak) or peak < 0.45:
        raise RecipeError("Аудиозаписи не дали надёжного совпадения: peak {:.3f}".format(peak))
    # A different strong peak means a periodic sound/repeated phrase could align in two places.
    separate = max(1, int(0.05 * RATE))
    alternatives = score.copy()
    alternatives[max(0, best - separate):min(len(score), best + separate + 1)] = -1.0
    second = float(np.max(alternatives)) if len(score) > 2 * separate + 1 else -1.0
    if second > peak * 0.87:
        raise RecipeError("Неоднозначное совпадение звука: несколько похожих сдвигов")
    lag = search_at + best / RATE - reference_at
    return {"reference_at_seconds": round(reference_at, 4), "lag_seconds": round(lag, 4),
            "correlation": round(peak, 4), "next_peak": round(second, 4)}


def _sync_window(reference, target, at, window, max_lag, ref_info, target_info):
    ref = _audio_window(reference, at, window, ref_info)
    search_at = max(0.0, at - max_lag)
    search_end = min(float(target_info["duration"]), at + window + max_lag)
    seek = extract_mono_audio(target, search_at, search_end - search_at, RATE)
    return _match(ref, seek, at, search_at)


def audio_sync(opt) -> dict:
    """Measure target-minus-reference offset at two distant windows and reject clock drift."""
    reference, target = require_input(opt.reference), require_input(opt.target)
    if reference == target:
        raise RecipeError("Для синхронизации нужны два разных файла")
    ref_info, target_info = probe(reference), probe(target)
    if not ref_info["has_audio"] or not target_info["has_audio"]:
        raise RecipeError("У обоих файлов нужна аудиодорожка")
    at, window, max_lag = float(opt.at), float(opt.window), float(opt.max_lag)
    if window < 1 or window > 30 or not 0 < max_lag <= MAX_LAG or at < max_lag:
        raise RecipeError("Нужны --window 1–30 с, --max-lag (0, 10] с и --at не раньше max-lag")
    first = _sync_window(reference, target, at, window, max_lag, ref_info, target_info)
    latest = min(ref_info["duration"], target_info["duration"]) - window - max_lag - 0.2
    windows = [first]
    status = "single_window"
    drift = None
    if latest - at >= max(window, 2.0):
        last = _sync_window(reference, target, latest, window, max_lag, ref_info, target_info)
        windows.append(last)
        drift = round(last["lag_seconds"] - first["lag_seconds"], 4)
        if abs(drift) > 0.05:
            raise RecipeError("Обнаружено расхождение часов/скорости (clock drift): {:.3f} с между окнами".format(drift))
        status = "confident"
    result = {"kind": "audio-sync", "reference": str(reference), "target": str(target),
              "lag_seconds": first["lag_seconds"], "target_shift_seconds": round(-first["lag_seconds"], 4),
              "status": status, "drift_seconds": drift, "windows": windows,
              "convention": "Положительный lag: то же событие в target позже, чем в reference; target_shift=-lag.",
              "note": "Только измерение. Сверьте хлопок/речь в начале и конце; файлы не изменены."}
    return _store(opt, result)


def register(subparsers) -> None:
    scene = subparsers.add_parser("scenes", help="найти границы смены плана (PySceneDetect)")
    scene.add_argument("source")
    scene.add_argument("--detector", choices=("content", "adaptive"), default="content")
    scene.add_argument("--threshold", type=float)
    scene.add_argument("--min-scene", type=float, default=0.6, help="минимальная длина сцены в секундах")
    scene.add_argument("--start", type=float, default=0.0)
    scene.add_argument("--end", type=float)
    scene.add_argument("--output", help="необязательный JSON-файл отчёта")
    scene.add_argument("--replace", action="store_true")
    scene.set_defaults(handler=scenes)

    report = subparsers.add_parser("audio-report", help="измерить ограниченный фрагмент аудио")
    report.add_argument("source")
    report.add_argument("--at", type=float, default=0.0)
    report.add_argument("--window", type=float, default=30.0)
    report.add_argument("--output", help="необязательный JSON-файл отчёта")
    report.add_argument("--replace", action="store_true")
    report.set_defaults(handler=audio_report)

    sync = subparsers.add_parser("audio-sync", help="измерить сдвиг двух аудиодорожек")
    sync.add_argument("reference")
    sync.add_argument("target")
    sync.add_argument("--at", type=float, default=5.0)
    sync.add_argument("--window", type=float, default=5.0)
    sync.add_argument("--max-lag", type=float, default=2.0)
    sync.add_argument("--output", help="необязательный JSON-файл отчёта")
    sync.add_argument("--replace", action="store_true")
    sync.set_defaults(handler=audio_sync)

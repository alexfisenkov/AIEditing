"""Small, explicit subtitle, stabilization and aligned quality recipes."""
from __future__ import annotations

import json
import math
import re
import shutil
import tempfile
from pathlib import Path

from .common import RecipeError, ffmpeg, output_file, probe, require_input

SUBTITLE_FORMATS = {".srt": "srt", ".ass": "ass", ".vtt": "vtt"}


def _vtt_style_features(path):
    if path.suffix.lower() != ".vtt":
        return []
    raw = path.read_text(encoding="utf-8-sig")
    found = []
    if re.search(r"(?m)^STYLE\s*$", raw):
        found.append("style_block")
    if re.search(r"(?m)^REGION\s*$", raw):
        found.append("region_block")
    for line in raw.splitlines():
        if re.match(r"\s*(?:\d+:)?\d{2}:\d{2}\.\d{3}\s+-->", line):
            if len(line.split("-->", 1)[1].strip().split()) > 1:
                found.append("cue_settings")
                break
    if re.search(r"<(?:v(?:\s|>)|c(?:\.|>)|lang(?:\s|>)|ruby>|rt>|\d{2}:)", raw):
        found.append("cue_markup")
    return found


def _subtitle_source(path, allow_style_loss=False):
    path = require_input(path)
    if path.suffix.lower() not in SUBTITLE_FORMATS:
        raise RecipeError("Поддерживаются субтитры SRT, ASS и VTT")
    try:
        import pysubs2

        features = _vtt_style_features(path)
        if features and not allow_style_loss:
            raise RecipeError("pysubs2 does not preserve styled WebVTT settings/CSS. Preserve that source or "
                              "use --allow-style-loss only when a plain-cue conversion is intended.")
        return path, pysubs2.load(str(path), encoding="utf-8"), features
    except (UnicodeError, ValueError) as exc:
        raise RecipeError("Не удалось прочесть субтитры как UTF-8: {}".format(exc)) from exc


def _check_events(subs, duration=None):
    events = [event for event in subs.events if event.type == "Dialogue"]
    if not events:
        raise RecipeError("В субтитрах нет реплик")
    for index, event in enumerate(events, 1):
        if event.start < 0 or event.end <= event.start:
            raise RecipeError("Некорректные времена реплики {}".format(index))
        if duration is not None and event.end > (duration + 0.1) * 1000:
            raise RecipeError("Реплика {} заканчивается после видео; проверьте синхронизацию".format(index))
    return events


def subtitle_convert(opt) -> dict:
    source, subs, features = _subtitle_source(opt.source, opt.allow_style_loss)
    target = Path(opt.output).expanduser().resolve()
    fmt = SUBTITLE_FORMATS.get(target.suffix.lower())
    if fmt is None:
        raise RecipeError("Выход субтитров должен иметь расширение .srt, .ass или .vtt")
    if (opt.from_fps is None) != (opt.to_fps is None):
        raise RecipeError("Для исправления частоты кадров задайте оба значения: --from-fps и --to-fps")
    if opt.from_fps is not None:
        if not math.isfinite(opt.from_fps) or not math.isfinite(opt.to_fps) or min(opt.from_fps, opt.to_fps) <= 0:
            raise RecipeError("Частота кадров должна быть положительным конечным числом")
        subs.transform_framerate(opt.from_fps, opt.to_fps)
    if opt.shift_ms:
        subs.shift(ms=opt.shift_ms)
    events = _check_events(subs)
    with output_file(target, replace=opt.replace, sources=(source,)) as staged:
        subs.save(str(staged), encoding="utf-8", format_=fmt)
    return {"output": str(target), "events": len(events), "format": fmt, "shift_ms": opt.shift_ms,
            "style_loss": bool(features) or (source.suffix.lower() in (".ass", ".vtt") and
                          fmt != SUBTITLE_FORMATS[source.suffix.lower()]),
            "style_loss_features": features,
            "note": "Таймкоды масштабированы по отношению частот, а не перенесены через монтажный список" if opt.from_fps else ""}


def _plain_lines(event) -> list[str]:
    import re

    text = re.sub(r"\{[^{}]*\}", "", event.text).replace(r"\N", "\n").replace(r"\n", "\n")
    return text.splitlines() or [text]


def subtitle_burn(opt) -> dict:
    video = require_input(opt.video)
    source, subs, features = _subtitle_source(opt.subtitles, opt.allow_style_loss)
    info = probe(video)
    if not info["has_video"]:
        raise RecipeError("В исходнике нет видеодорожки")
    events = _check_events(subs, info["duration"])
    font = require_input(opt.font_file) if opt.font_file else None
    if font and font.suffix.lower() not in (".ttf", ".otf"):
        raise RecipeError("Шрифт должен быть файлом .ttf или .otf")
    if font and not opt.font_family:
        raise RecipeError("Для файла шрифта укажите его семейство через --font-family")
    if opt.font_size is not None and not 8 <= opt.font_size <= 200:
        raise RecipeError("Размер шрифта должен быть от 8 до 200")
    if opt.bottom_safe is not None and not 0.05 <= opt.bottom_safe <= 0.4:
        raise RecipeError("Нижняя безопасная зона должна быть от 0.05 до 0.40 высоты кадра")
    imported_ass = source.suffix.lower() == ".ass"
    if imported_ass and not opt.restyle and (opt.font_size is not None or opt.bottom_safe is not None or
                                            (opt.font_family and not font)):
        raise RecipeError("ASS сохраняет исходный стиль; для изменения размера, семейства или полей добавьте --restyle")
    if imported_ass and not opt.restyle and font and opt.font_family:
        families = {subs.styles[event.style].fontname.casefold() for event in events if event.style in subs.styles}
        for event in events:
            families.update(name.strip().casefold() for name in re.findall(r"\\fn([^\\}]+)", event.text))
        if opt.font_family.casefold() not in families:
            raise RecipeError("ASS does not request this font family; choose its font file or use --restyle")
    if not imported_ass or opt.restyle:
        import pysubs2
        from runtime.media.vertical import shown_size

        width, height = shown_size(info)
        subs.info["PlayResX"], subs.info["PlayResY"] = str(width), str(height)
        margin = opt.bottom_safe if opt.bottom_safe is not None else (0.25 if height > width else 0.12)
        size = opt.font_size or max(12, round(height * (0.042 if height > width else 0.048)))
        style = pysubs2.SSAStyle(fontname=opt.font_family or "Arial", fontsize=size, bold=True,
                                outline=max(1, size * 0.06), shadow=0,
                                alignment=pysubs2.Alignment.BOTTOM_CENTER,
                                marginl=round(width * 0.08), marginr=round(width * 0.08),
                                marginv=round(height * margin))
        if imported_ass:
            for name in subs.styles:
                subs.styles[name] = style.copy()
        else:
            subs.styles["Default"] = style
    target = Path(opt.output).expanduser().resolve()
    if target.suffix.lower() != ".mp4":
        raise RecipeError("Результат с вшитыми субтитрами должен быть .mp4")
    with tempfile.TemporaryDirectory(prefix="aiediting-ass-") as raw:
        safe = Path(raw)
        (safe / "fonts").mkdir()
        if font:
            shutil.copy2(font, safe / "fonts" / ("font" + font.suffix.lower()))
        subs.save(str(safe / "sub.ass"), encoding="utf-8", format_="ass")
        with output_file(target, replace=opt.replace, sources=(video, source)) as staged:
            ffmpeg(["-i", str(video), "-map", "0:v:0", "-map", "0:a?", "-vf",
                    "ass=filename=sub.ass:fontsdir=fonts", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(staged)],
                   cwd=safe)
            result = probe(staged)
            if not result["has_video"] or (info["has_audio"] and not result["has_audio"]):
                raise RecipeError("После вшивания потеряна дорожка видео или звука")
            if abs(result["duration"] - info["duration"]) > max(0.15, 1 / max(info["fps"], 1)):
                raise RecipeError("После вшивания изменилась длительность видео")
    longest = max(len(line) for event in events for line in _plain_lines(event))
    return {"output": str(target), "events": len(events), "longest_line_chars": longest,
            "font_source": "bundled-file-rendering-unverified" if font else "system-font-unverified",
            "style_loss_features": features,
            "ass_style_preserved": imported_ass and not opt.restyle,
            "review": "Проверьте шрифт, переносы, безопасную зону и кадр посередине каждой реплики"}


def stabilize(opt) -> dict:
    source = require_input(opt.source)
    info = probe(source)
    if not info["has_video"]:
        raise RecipeError("В исходнике нет видеодорожки")
    start = opt.start or 0.0
    duration = opt.duration if opt.duration is not None else info["duration"] - start
    if not math.isfinite(start) or not math.isfinite(duration) or start < 0 or duration <= 0 or start + duration > info["duration"] + 0.05:
        raise RecipeError("Отрезок стабилизации выходит за длительность исходника")
    if not 0 <= opt.smoothing <= 1000:
        raise RecipeError("smoothing должен быть от 0 до 1000 кадров")
    target = Path(opt.output).expanduser().resolve()
    if target.suffix.lower() != ".mp4":
        raise RecipeError("Результат стабилизации должен быть .mp4")
    clip = ["-ss", "{:.6f}".format(start), "-i", str(source), "-t", "{:.6f}".format(duration)]
    with tempfile.TemporaryDirectory(prefix="aiediting-vidstab-") as raw:
        safe = Path(raw)
        ffmpeg(clip + ["-map", "0:v:0", "-vf", "vidstabdetect=result=transforms.trf:shakiness=5:accuracy=15",
                       "-an", "-f", "null", "-"], cwd=safe)
        if not (safe / "transforms.trf").is_file() or (safe / "transforms.trf").stat().st_size == 0:
            raise RecipeError("Первый проход не создал преобразования стабилизации")
        with output_file(target, replace=opt.replace, sources=(source,)) as staged:
            ffmpeg(clip + ["-map", "0:v:0", "-map", "0:a?", "-vf",
                           "vidstabtransform=input=transforms.trf:smoothing={}:optzoom=1:crop=keep".format(opt.smoothing),
                           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", str(staged)], cwd=safe)
            output_info = probe(staged)
            if not output_info["has_video"] or (info["has_audio"] and not output_info["has_audio"]):
                raise RecipeError("Стабилизация потеряла видеодорожку или звук")
            if abs(output_info["duration"] - duration) > max(0.15, 1 / max(info["fps"], 1)):
                raise RecipeError("Длительность после стабилизации изменилась; проверьте отрезок")
    return {"output": str(target), "start": start, "duration": output_info["duration"],
            "smoothing": opt.smoothing, "review": "Проверьте края кадра, масштаб и стыки с соседними планами"}


def quality(opt) -> dict:
    from runtime.media.vertical import shown_size

    if not opt.aligned_same_content:
        raise RecipeError("VMAF требует подтверждения: оба файла — тот же материал с одинаковыми кадрами и таймингом")
    distorted, reference = require_input(opt.distorted), require_input(opt.reference)
    measured, original = probe(distorted), probe(reference)
    if not measured["has_video"] or not original["has_video"]:
        raise RecipeError("Для VMAF нужны две видеодорожки")
    if shown_size(measured) != shown_size(original) or measured["rotation"] != original["rotation"]:
        raise RecipeError("Видимые размеры или ориентация кадров различаются; сравнение VMAF не запущено")
    fps = measured["fps"]
    if fps <= 0 or abs(fps - original["fps"]) > 0.001:
        raise RecipeError("Частота кадров различается; сравнение VMAF не запущено")
    if abs(measured["duration"] - original["duration"]) > max(0.04, 1 / fps):
        raise RecipeError("Длительности различаются; сравнение VMAF не запущено")
    with tempfile.TemporaryDirectory(prefix="aiediting-vmaf-") as raw:
        safe = Path(raw)
        ffmpeg(["-i", str(distorted), "-i", str(reference), "-filter_complex",
                "[0:v]setpts=PTS-STARTPTS[dist];[1:v]setpts=PTS-STARTPTS[ref];"
                "[dist][ref]libvmaf=log_path=vmaf.json:log_fmt=json[v]",
                "-map", "[v]", "-an", "-f", "null", "-"], cwd=safe)
        try:
            data = json.loads((safe / "vmaf.json").read_text(encoding="utf-8"))
            score = float(data["pooled_metrics"]["vmaf"]["mean"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise RecipeError("FFmpeg не вернул проверяемую оценку VMAF") from exc
    if not math.isfinite(score):
        raise RecipeError("Оценка VMAF не является конечным числом")
    return {"vmaf": round(score, 3), "distorted": str(distorted), "reference": str(reference),
            "aligned_same_content": True, "model": "vmaf_v0.6.1",
            "limit": "Метаданные и флаг не доказывают совпадение кадров; визуально проверьте их выравнивание"}


def register(subparsers) -> None:
    convert = subparsers.add_parser("subtitle-convert", help="SRT/ASS/VTT conversion and retiming")
    convert.add_argument("source")
    convert.add_argument("output")
    convert.add_argument("--shift-ms", type=int, default=0)
    convert.add_argument("--from-fps", type=float)
    convert.add_argument("--to-fps", type=float)
    convert.add_argument("--replace", action="store_true")
    convert.add_argument("--allow-style-loss", action="store_true")
    convert.set_defaults(handler=subtitle_convert)

    burn = subparsers.add_parser("subtitle-burn", help="Burn subtitles with local ASS/font staging")
    burn.add_argument("video")
    burn.add_argument("subtitles")
    burn.add_argument("output")
    burn.add_argument("--font-file")
    burn.add_argument("--font-family")
    burn.add_argument("--font-size", type=int)
    burn.add_argument("--bottom-safe", type=float)
    burn.add_argument("--restyle", action="store_true")
    burn.add_argument("--replace", action="store_true")
    burn.add_argument("--allow-style-loss", action="store_true")
    burn.set_defaults(handler=subtitle_burn)

    stabilize_cmd = subparsers.add_parser("stabilize", help="Two-pass VidStab for one selected cut")
    stabilize_cmd.add_argument("source")
    stabilize_cmd.add_argument("output")
    stabilize_cmd.add_argument("--start", type=float, default=0.0)
    stabilize_cmd.add_argument("--duration", type=float)
    stabilize_cmd.add_argument("--smoothing", type=int, default=15)
    stabilize_cmd.add_argument("--replace", action="store_true")
    stabilize_cmd.set_defaults(handler=stabilize)

    metric = subparsers.add_parser("quality", help="VMAF for aligned same-content files only")
    metric.add_argument("distorted")
    metric.add_argument("reference")
    metric.add_argument("--aligned-same-content", action="store_true")
    metric.set_defaults(handler=quality)

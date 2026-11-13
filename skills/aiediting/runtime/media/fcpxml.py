"""A timeline as FCPXML 1.10, the plain subset DaVinci Resolve imports («Файл → Импорт → Таймлиния»).

spec = {"name", "fps", "width", "height", "duration", "video": [lane], "audio": [lane], "markers": [{"t", "text", "kind"}]};
lane = {"name", "role"?, "clips": [{"file", "start", "in", "dur", "muted"?, "off"?, "db"?}]}, seconds everywhere.
The first video lane is the main storyline (a hole in it is a gap); every other lane is connected to it: video lanes
above (1, 2, …), audio lanes below (−1, −2, …). Every time is a whole frame of the sequence counted from zero, so a
thousand short clips end where the timeline ends. `muted`: a video clip without its sound; `off`: on the timeline,
switched off; `db`: its level. `write_note` writes the person's note on how to open it. Standard library only and no package imports: the graphics kit loads this file by path.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

AUDIO = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".aif", ".aiff"}
STILL = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".heic"}
KINDS = {"chapter": "глава", "broll": "вставка", "edit": "правка"}


def frame_of(fps: float) -> Fraction:
    """Frame duration: 1001/30000 s for 29.97 (and the other NTSC rates), 1/n s for a whole rate."""
    fps = float(fps or 0)
    if fps <= 0:
        raise ValueError("Частота кадров таймлинии должна быть больше нуля, а не {}".format(fps))
    whole = round(fps)
    if abs(fps - whole) < 0.005:
        return Fraction(1, whole)
    ntsc = round(fps * 1.001)
    if abs(fps - ntsc / 1.001) < 0.005:
        return Fraction(1001, ntsc * 1000)
    return Fraction(1, 1) / Fraction(fps).limit_denominator(1001)


def _t(frames: int, frame: Fraction) -> str:
    value = frames * frame
    return "0s" if value == 0 else "{}/{}s".format(value.numerator, value.denominator)


class _Clock:
    def __init__(self, frame: Fraction):
        self.frame = frame

    def n(self, seconds) -> int:
        """Whole frames from zero: each moment is rounded on its own, never a sum of rounded lengths."""
        return int(round(Fraction(float(seconds)).limit_denominator(10 ** 6) / self.frame))

    def span(self, start, dur) -> Tuple[int, int]:
        a = self.n(start)
        return a, max(1, self.n(float(start) + float(dur)) - a)


def _kind(path: Path) -> str:
    ext = path.suffix.lower()
    return "audio" if ext in AUDIO else ("still" if ext in STILL else "video")


def _resources(spec: Dict, clock: _Clock, root) -> Dict[str, str]:
    res = ET.SubElement(root, "resources")
    ET.SubElement(res, "format", id="r1", name="AIEditing {}x{}".format(int(spec["width"]), int(spec["height"])),
                  frameDuration=_t(1, clock.frame), width=str(int(spec["width"])), height=str(int(spec["height"])))
    ET.SubElement(res, "format", id="r2", name="FFVideoFormatRateUndefined",
                  width=str(int(spec["width"])), height=str(int(spec["height"])))
    longest: Dict[str, int] = {}
    for lane in list(spec.get("video") or []) + list(spec.get("audio") or []):
        for c in lane.get("clips") or []:
            key = str(Path(c["file"]).expanduser().resolve())
            longest[key] = max(longest.get(key, 0), clock.n(float(c.get("in") or 0) + float(c["dur"])))
    ids = {}
    for k, (path, frames) in enumerate(sorted(longest.items())):
        kind, ids[path] = _kind(Path(path)), "r{}".format(k + 3)
        attrs = {"id": ids[path], "name": Path(path).stem, "start": "0s",
                 "duration": "0s" if kind == "still" else _t(frames, clock.frame)}
        if kind != "audio":
            attrs.update(hasVideo="1", format="r2" if kind == "still" else "r1", videoSources="1")
        if kind != "still":
            attrs.update(hasAudio="1", audioSources="1", audioChannels="2", audioRate="48000")
        asset = ET.SubElement(res, "asset", **attrs)
        ET.SubElement(asset, "media-rep", kind="original-media", src=Path(path).as_uri())
    return ids


def _item(parent, c: Dict, lane_name: str, ids: Dict, clock: _Clock, lane: int, at: int, role: str):
    path = str(Path(c["file"]).expanduser().resolve())
    start, dur = clock.span(c["start"], c["dur"])
    still = _kind(Path(path)) == "still"
    attrs = {"ref": ids[path], "name": "{} · {}".format(lane_name, Path(path).stem), "offset": _t(at, clock.frame),
             "start": _t(0 if still else clock.n(c.get("in") or 0), clock.frame), "duration": _t(dur, clock.frame)}
    if lane:
        attrs["lane"] = str(lane)
    if c.get("off"):
        attrs["enabled"] = "0"
    if not still:
        if c.get("muted"):
            attrs["srcEnable"] = "video"
        elif _kind(Path(path)) == "audio" or lane < 0:
            attrs["audioRole"] = role
    el = ET.SubElement(parent, "video" if still else "asset-clip", **attrs)
    if c.get("db") is not None and not still:
        ET.SubElement(el, "adjust-volume", amount="{:g}dB".format(float(c["db"])))
    return el


def _spine(spec: Dict, clock: _Clock, seq, ids: Dict, total: int) -> List[Tuple[int, int, int, object]]:
    """The main lane, holes filled with gaps: [(offset, length, own start, element)] in frames."""
    spine, parts, at = ET.SubElement(seq, "spine"), [], 0
    main = (spec.get("video") or [{"name": "", "clips": []}])[0]
    for c in sorted(main.get("clips") or [], key=lambda c: float(c["start"])):
        start, dur = clock.span(c["start"], c["dur"])
        if start > at:
            parts.append((at, start - at, 0, ET.SubElement(spine, "gap", name="Пусто", offset=_t(at, clock.frame),
                                                            start="0s", duration=_t(start - at, clock.frame))))
        el = _item(spine, c, main["name"], ids, clock, 0, max(start, at), "dialogue")
        parts.append((max(start, at), dur, 0 if el.tag == "video" else clock.n(c.get("in") or 0), el))
        at = max(start, at) + dur
    if at < total or not parts:
        parts.append((at, max(1, total - at), 0, ET.SubElement(spine, "gap", name="Пусто", offset=_t(at, clock.frame),
                                                                  start="0s", duration=_t(max(1, total - at), clock.frame))))
    return parts


def _host(parts, at: int):
    """The element of the main lane that plays at frame `at`, and that frame in the element's own time."""
    for offset, length, own, el in parts:
        if offset <= at < offset + length:
            return el, own + at - offset
    offset, _length, own, el = parts[-1]
    return el, own + at - offset


def _check(spec: Dict) -> None:
    lanes = list(spec.get("video") or []) + list(spec.get("audio") or [])
    if not any(lane.get("clips") for lane in lanes):
        raise ValueError("В таймлинии нет ни одного клипа")
    for key in ("width", "height"):
        if int(spec.get(key) or 0) <= 0:
            raise ValueError("У таймлинии нет размера кадра ({})".format(key))


def write(spec: Dict, out: Path) -> Path:
    """Writes the timeline to `out` (atomically) and returns it."""
    clock = _Clock(frame_of(spec.get("fps")))
    _check(spec)
    total = clock.n(spec["duration"])
    root = ET.Element("fcpxml", version="1.10")
    ids = _resources(spec, clock, root)
    project = ET.SubElement(ET.SubElement(ET.SubElement(root, "library"), "event", name=spec["name"]),
                            "project", name=spec["name"])
    seq = ET.SubElement(project, "sequence", format="r1", duration=_t(total, clock.frame), tcStart="0s",
                        tcFormat="NDF", audioLayout="stereo", audioRate="48k")
    parts = _spine(spec, clock, seq, ids, total)
    above = [(k + 1, lane) for k, lane in enumerate((spec.get("video") or [])[1:])]
    below = [(-(k + 1), lane) for k, lane in enumerate(spec.get("audio") or [])]
    for number, lane in above + below:
        for c in sorted(lane.get("clips") or [], key=lambda c: float(c["start"])):
            host, at = _host(parts, clock.n(c["start"]))
            _item(host, c, lane["name"], ids, clock, number, at, lane.get("role") or "dialogue")
    for m in sorted(spec.get("markers") or [], key=lambda m: float(m["t"])):
        host, at = _host(parts, clock.n(m["t"]))
        ET.SubElement(host, "marker", start=_t(at, clock.frame), duration=_t(1, clock.frame), value=str(m["text"]),
                      note=KINDS.get(str(m.get("kind")), str(m.get("kind") or "")))
    return _save(root, Path(out))


def _save(root, out: Path) -> Path:
    if hasattr(ET, "indent"):  # Python 3.9+
        ET.indent(root)
    return _text(out, '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + ET.tostring(root, encoding="unicode") + "\n")


def _text(out: Path, text: str) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(str(tmp), str(out))
    return out


def _lane_line(lane: Dict, where: str) -> str:
    clips = lane.get("clips") or []
    off = " (выключен — включите, если нужен)" if clips and all(c.get("off") for c in clips) else ""
    return "- {} — «{}»: клипов {}{}".format(where, lane["name"], len(clips), off)


def write_note(spec: Dict, timeline: Path, out: Path, video: str, extra: Sequence[str] = ()) -> Path:
    """`таймлиния.md` for the person: how to open the file in DaVinci Resolve, what lies where, what to do if not."""
    video_lanes, audio_lanes = list(spec.get("video") or []), list(spec.get("audio") or [])
    folders = sorted({str(Path(c["file"]).expanduser().resolve().parent) for lane in video_lanes + audio_lanes
                      for c in lane.get("clips") or []})
    kinds = sorted({KINDS.get(str(m.get("kind")), "") for m in spec.get("markers") or []} - {""})
    lines = ["# Таймлиния: {}".format(spec["name"]), "",
             "Файл `{}` — таймлиния монтажа для DaVinci Resolve 18 и новее (формат FCPXML 1.10). Готовый ролик `{}` "
             "от неё не зависит: таймлиния нужна, чтобы увидеть монтаж и поправить его руками.".format(timeline.name, video),
             "", "## Как открыть", "",
             "1. Откройте DaVinci Resolve и проект — любой, можно новый.",
             "2. Файл → Импорт → Таймлиния (File → Import → Timeline) и выберите `{}`.".format(timeline),
             "3. Таймлиния появится в пуле медиа (Media Pool): откройте её двойным щелчком.", "",
             "## Что на какой дорожке", ""]
    lines += [_lane_line(lane, "видео {}{}".format(k + 1, ", нижняя" if k == 0 else ", выше")) for k, lane in enumerate(video_lanes)]
    lines += [_lane_line(lane, "звук {}".format(k + 1)) for k, lane in enumerate(audio_lanes)]
    if kinds:
        lines.append("- маркеры с текстом: {}".format(", ".join(kinds)))
    lines += ["- {}".format(x) for x in extra]
    lines += ["", "## Если клипы красные (файл не найден)", "",
              "Файлы переехали или открыты на другом компьютере. В пуле медиа выделите красные клипы → правой кнопкой → "
              "Relink Selected Clips → укажите папку, где файлы лежат сейчас. Папки, записанные в таймлинии:", ""]
    lines += ["- `{}`".format(f) for f in folders]
    lines += ["", "## Если какой-то слой не перенёсся", "",
              "Как переносятся картинки поверх видео, маркеры, громкость и выключенные варианты, зависит от версии "
              "Resolve. Чего не оказалось на таймлинии, смотрите в готовом ролике `{}`: он эталон, время в нём то же, что "
              "у маркеров. Картинку или звук можно перетащить из пула медиа на дорожку руками, по маркерам.".format(video)]
    return _text(Path(out), "\n".join(lines) + "\n")

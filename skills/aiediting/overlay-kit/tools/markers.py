#!/usr/bin/env python3
"""Markers from a Final Cut export: python3 markers.py <folder.fcpxmld | Info.fcpxml> <out.json>
A marker's time = clip offset + marker start - clip start. Prints a check of the file and writes the list of remarks."""
import json
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

FPS = 30


def sec(value):
    return Fraction(value.rstrip("s")) if value else Fraction(0)


def timecode(seconds):
    minutes, rest = divmod(round(seconds * FPS), 60 * FPS)
    whole, frames = divmod(rest, FPS)
    return f"{minutes:02d}:{whole:02d}:{frames:02d}"


def read_markers(path):
    src = Path(path)
    if src.is_dir():
        src = src / "Info.fcpxml"
    if not src.is_file():
        raise SystemExit(f"Нет файла {src}")
    root = ET.parse(src).getroot()
    seq = root.find(".//sequence")
    if seq is None:
        raise SystemExit("В выгрузке нет последовательности: выгружать проект, а не клип")
    markers = []
    for clip in seq.find("spine"):
        offset, start = sec(clip.get("offset")), sec(clip.get("start"))
        for mark in clip.iter():
            if mark.tag in ("marker", "chapter-marker"):
                at = offset + sec(mark.get("start")) - start
                markers.append({"t": float(at), "tc": timecode(at), "text": (mark.get("value") or "").strip(), "note": mark.get("note")})
    markers.sort(key=lambda m: m["t"])
    return markers, float(sec(seq.get("duration")))


def main(argv):
    if len(argv) != 2:
        raise SystemExit("Нужно два пути: выгрузка Final Cut и файл результата")
    markers, length = read_markers(argv[0])
    print("длина", length, "маркеров", len(markers))
    print("пустых подписей:", sum(1 for m in markers if not m["text"]), "вне длины ролика:", sum(1 for m in markers if m["t"] > length))
    Path(argv[1]).write_text(json.dumps(markers, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])

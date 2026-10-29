"""Helpers for the pipeline tests: a fake recogniser that 'hears' tone bursts, approvers, loudness, hashes.

The fake recogniser finds tone bursts in the audio with ffmpeg and names each by its length from a table,
so after a cut it hears exactly the words whose bursts survived — a stand-in for a second listening.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

FAKE_ASR = r'''
import json, re, subprocess, sys
media, table = sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8"))
if "words" in table:
    print(json.dumps({"words": table["words"]}, ensure_ascii=False)); sys.exit(0)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                            "default=nw=1:nk=1", media], stdout=subprocess.PIPE, text=True).stdout)
err = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", media, "-vn", "-af",
                      "silencedetect=noise=-35dB:d=0.08", "-f", "null", "-"],
                     stderr=subprocess.PIPE, text=True).stderr
cuts, start = [], None
for line in err.splitlines():
    m = re.search(r"silence_start: (-?[\d.]+)", line)
    if m: start = max(0.0, float(m.group(1)))
    m = re.search(r"silence_end: (-?[\d.]+)", line)
    if m and start is not None: cuts.append((start, float(m.group(1)))); start = None
if start is not None: cuts.append((start, dur))
runs, cur = [], 0.0
for a, b in cuts:
    if a - cur > 0.1: runs.append((cur, a))
    cur = b
if dur - cur > 0.1: runs.append((cur, dur))
words = []
for a, b in runs:
    length, text = min(((abs((b - a) - L), t) for L, t in table["bursts"]))
    if length <= 0.05: words.append({"text": text, "start": round(a, 3), "end": round(b, 3)})
print(json.dumps({"words": words}, ensure_ascii=False))
'''

# Lesson: tone bursts whose lengths name the words (seconds); 3.3–4.5 is a long pause.
LESSON = [(0.50, 1.00, "Привет"), (1.20, 1.40, "ну"), (1.60, 2.00, "э-э"), (2.20, 2.80, "сегодня"),
          (3.00, 3.30, "мы."), (4.50, 5.10, "сегодня"), (5.30, 5.60, "мы"), (5.80, 6.50, "смотрите"),
          (6.70, 7.50, "говорим."), (7.70, 8.60, "Опус")]
LESSON_SECONDS = 9.2


def bursts(spec):
    """{"bursts": [[length, word], ...]} from [(start, end, word)]."""
    seen = {}
    for a, b, w in spec:
        seen[round(b - a, 2)] = w
    return {"bursts": [[k, v] for k, v in sorted(seen.items())]}


def asr_config(tmp, table):
    tmp = Path(tmp)
    script, data = tmp / "fake_asr.py", tmp / "слова.json"
    script.write_text(FAKE_ASR, encoding="utf-8")
    data.write_text(json.dumps(table, ensure_ascii=False), encoding="utf-8")
    return {"provider": "command", "language": "ru",
            "command": [sys.executable, str(script), "{input}", str(data)]}


def hear(tmp, video, table):
    """What the fake recogniser hears in `video`: the word texts."""
    cfg = asr_config(tmp, table)
    out = subprocess.run(cfg["command"][:2] + [str(video), cfg["command"][3]], stdout=subprocess.PIPE,
                         check=True).stdout
    return [w["text"] for w in json.loads(out.decode("utf-8"))["words"]]


class Approver:
    """Says `default` to everything; `edits[key](payload)` corrects the payload first; logs the keys."""

    def __init__(self, default=True, answers=None, edits=None):
        self.default, self.answers, self.edits, self.asked = default, answers or {}, edits or {}, []

    def __call__(self, key, payload):
        json.dumps(payload)  # must be JSON-safe: the format skill writes it to вопросы.json
        self.asked.append(key)
        if key in self.edits:
            self.edits[key](payload)
        return self.answers.get(key, self.default)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def loudness(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-vn", "-af",
                          "loudnorm=print_format=json", "-f", "null", "-"],
                         stderr=subprocess.PIPE, encoding="utf-8", errors="replace").stderr
    return float(json.loads(re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S)[-1])["input_i"])


def profile(steps, asr, **params):
    return {"format": "проба", "skill_name": "монтаж-проба", "language": "ru", "asr": asr,
            "steps": steps, "params": params, "output_dir": "выпуски"}

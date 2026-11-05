#!/usr/bin/env python3
"""Clean speech from a recording: several takes, or a whole recording with its edges trimmed. Run in the AIEditing environment (numpy).
  takes.py init <video> <config.json> --out <dir> [--speed S] --model <ggml file> --language ru [--prompt P] [--force]
                                 config.json for this recording: its sound as mono 48 kHz, spans for the recogniser
  takes.py words <config.json>   word times of every recording, at its own speed: out/words.json, out/words-lines.txt to choose takes from
  takes.py plan  <config.json>   the chosen takes become pieces, pauses out: out/pieces.json, out/speech-text.txt
  takes.py trim  <config.json>   the recording stays whole, only its edges go: the same two files
Then `recut.py build` makes the video. config.json:
{"out": "<dir>", "speed": 1.07, "language": "ru", "whisper_model": "<ggml file>", "prompt": "names the recogniser mishears",
 "recordings": {"A": {"video": "<file>", "audio": "<mono 48 kHz wav>"}},
 "segments": {"A": [[0, 438]]},                  // spans with speech, recognised in pieces: a long file makes the recogniser loop
 "takes": [["A", 0, "first words", "last words"]],  // in the order of the video; seconds = search from there
 "exclude": [["A", 28.4, 43.0]],                 // something else inside a take, seconds of the recording
 "trim": {"A": [1.2, 890.5]}}                    // `trim` only, optional: the edges by hand, seconds of the recording
`speed` is `params.speed`, the rate of the finished video: pieces.json and every marker are in its seconds. Nothing here plays
faster: the speed goes on once, in `run.py edit`.
"""
import argparse
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # Windows: Russian lines must not stop a run before its file is written
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

VAD_DB = -44
PAD_START, PAD_INNER, PAD_LAST = 0.05, 0.08, 0.15
JOIN = 0.3
SETTLE = 0.45  # how far a word's edge may move to where the sound really ends: a recogniser's word times are off by tenths
SHORT = 0.6


def load(path):
    cfg = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    out = Path(cfg["out"]).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    return cfg, out


def norm(text):
    return re.sub(r"[^\w-]", "", text.lower().replace("ё", "е"))


def words(cfg, out):
    found = []
    for rec, spans in cfg["segments"].items():
        audio = cfg["recordings"][rec]["audio"]
        for a, b in spans:
            piece = out / f"piece-{rec}-{a}"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", str(b - a), "-i", audio, "-ar", "16000", "-ac", "1", f"{piece}.wav"], check=True)
            cmd = ["whisper-cli", "-m", cfg["whisper_model"], "-l", cfg.get("language", "ru"), "-mc", "0", "-ml", "1", "-sow", "-oj", "-f", f"{piece}.wav", "-of", str(piece), "--no-prints"]
            if cfg.get("prompt"):
                cmd += ["--prompt", cfg["prompt"]]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
            for seg in json.loads(Path(f"{piece}.json").read_text(encoding="utf-8"))["transcription"]:
                text = seg["text"].strip()
                if text and not text.startswith("[_"):
                    found.append({"c": rec, "a": round(a + seg["offsets"]["from"] / 1000, 2), "b": round(a + seg["offsets"]["to"] / 1000, 2), "t": text})
            print("готово", rec, a, flush=True)
    (out / "words.json").write_text(json.dumps(found, ensure_ascii=False), encoding="utf-8")
    lines, buf = [], []
    for i, w in enumerate(found):
        if not buf or w["a"] - found[i - 1]["b"] > 0.8 or len(buf) >= 10 or found[i - 1]["c"] != w["c"]:
            if buf:
                lines.append(" ".join(buf))
            buf = [f'{w["c"]} {w["a"]:.1f}|']
        buf.append(w["t"])
    if buf:
        lines.append(" ".join(buf))
    (out / "words-lines.txt").write_text("\n".join(lines), encoding="utf-8")
    print("слов", len(found), "строк", len(lines))


def loudness(audio_path):
    """True per 20 ms where there is sound."""
    import numpy as np

    with wave.open(audio_path) as f:
        rate = f.getframerate()
        pcm = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    step = rate // 50
    n = len(pcm) // step
    db = 20 * np.log10(np.sqrt((pcm[:n * step].reshape(n, step) ** 2).mean(axis=1)) + 1e-9)
    return db > VAD_DB


def settled(vad, a, b, prev_end, next_start):
    """A word's real edges: the sound inside it, then outward while the sound goes on, never into a neighbour."""
    import numpy as np

    lo, hi = int(a * 50), max(int(b * 50), int(a * 50) + 1)
    on = np.flatnonzero(vad[lo:hi])
    if not len(on):
        return None, None
    start, end = lo + int(on[0]), lo + int(on[-1]) + 1
    floor = max(int((a - SETTLE) * 50), int(prev_end * 50))
    ceil = min(int((b + SETTLE) * 50), int(next_start * 50), len(vad))
    while start > floor and start > 0 and vad[start - 1]:
        start -= 1
    while end < ceil and vad[end]:
        end += 1
    return start / 50, end / 50


def plan(cfg, out):
    raw = json.loads((out / "words.json").read_text(encoding="utf-8"))
    (out / "time-map.json").unlink(missing_ok=True)  # mutes of an earlier plan must not land on this speech
    by_rec = {}
    for rec, item in cfg["recordings"].items():
        vad = loudness(item["audio"])
        items = [w for w in raw if w["c"] == rec and norm(w["t"])]
        rows = []
        for i, w in enumerate(items):
            prev_end = items[i - 1]["b"] if i else 0
            next_start = items[i + 1]["a"] if i + 1 < len(items) else w["b"] + SETTLE
            a, b = settled(vad, w["a"], w["b"], prev_end, next_start)
            rows.append((a, b, norm(w["t"]), w["t"], w["a"]))
        by_rec[rec] = rows

    def find(rec, start, pattern):
        rows = by_rec[rec]
        for i, w in enumerate(rows):
            if w[4] >= start and all(i + j < len(rows) and rows[i + j][2] == p for j, p in enumerate(pattern)):
                return i
        return None

    pieces, problems, script = [], [], []
    for idx, (rec, start, first, last) in enumerate(cfg["takes"]):
        head = [norm(x) for x in first.split()]
        tail = [norm(x) for x in last.split()]
        i = find(rec, start, head)
        if i is None:
            problems.append(f"нет начала #{idx}: {first} (с {start})")
            continue
        j = find(rec, by_rec[rec][i][4], tail)
        if j is None:
            problems.append(f"нет конца #{idx}: {last}")
            continue
        j += len(tail) - 1
        spans = []
        for w in by_rec[rec][i:j + 1]:
            if w[0] is None:
                continue
            if spans and w[0] - spans[-1][1] <= JOIN:
                spans[-1][1] = max(spans[-1][1], w[1])
            else:
                spans.append([w[0], w[1]])
        holes = sorted(x[1:] for x in cfg.get("exclude", []) if x[0] == rec)
        parts = []
        for s in spans:
            cur = s[0]
            for xa, xb in holes:
                if xb <= cur or xa >= s[1]:
                    continue
                if xa > cur:
                    parts.append([cur, xa, True])
                cur = max(cur, xb)
            if cur < s[1]:
                parts.append([cur, s[1], False])
        for n, part in enumerate(parts):
            a = round(max(0, part[0] - (0 if n and parts[n - 1][2] else PAD_START)) * 30) / 30
            b = round((part[1] + (0 if part[2] else (PAD_LAST if n == len(parts) - 1 else PAD_INNER))) * 30) / 30
            if pieces and pieces[-1]["c"] == rec and a < pieces[-1]["b"]:
                a = pieces[-1]["b"]
            if b - a >= 0.1:
                pieces.append({"c": rec, "a": a, "b": b, "clip": idx})
        script.append(f"#{idx} " + " ".join(w[3] for w in by_rec[rec][i:j + 1]))
    speed = cfg.get("speed", 1.0)
    at = 0.0
    for p in pieces:
        d = (p["b"] - p["a"]) / speed
        p["from"], p["to"] = round(at, 4), round(at + d, 4)
        at += d
    (out / "pieces.json").write_text(json.dumps(pieces, ensure_ascii=False), encoding="utf-8")
    (out / "speech-text.txt").write_text("\n".join(script), encoding="utf-8")
    print("кусков", len(pieces), "длина", round(at, 1))
    print("\n".join(problems) or "все дубли найдены")
    print("короткие куски, прослушать каждый:", [(p["from"], round(p["to"] - p["from"], 2)) for p in pieces if p["to"] - p["from"] < SHORT])


def _init(argv):
    import takes_whole

    ap = argparse.ArgumentParser(prog="takes.py init")
    ap.add_argument("video")
    ap.add_argument("config")
    ap.add_argument("--out", required=True)
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--model", required=True)
    ap.add_argument("--language", required=True)
    ap.add_argument("--prompt", default="")
    ap.add_argument("--force", action="store_true")
    opt = ap.parse_args(argv)
    takes_whole.init(opt.video, opt.config, opt.out, opt.speed, opt.model, opt.language, opt.prompt, opt.force)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        _init(sys.argv[2:])
        raise SystemExit(0)
    if len(sys.argv) != 3 or sys.argv[1] not in ("words", "plan", "trim"):
        raise SystemExit(__doc__)
    config, folder = load(sys.argv[2])
    if sys.argv[1] == "trim":
        import takes_whole

        takes_whole.trim(config, folder)
    else:
        {"words": words, "plan": plan}[sys.argv[1]](config, folder)

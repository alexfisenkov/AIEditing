#!/usr/bin/env python3
"""Edit a clean-speech cut by markers without moving the scenes. Run in the AIEditing environment (numpy).
  recut.py plan   <config.json>   applies the edits to out/pieces.json: new pieces and src/data/time-map.json contents
  recut.py build  <config.json>   the speech as a video: batches of frames, audio with micro-fades, mutes, speed
  recut.py joins  <config.json>   recognises the audio around every join: what is heard after the edit
config.json:
{"out": "<dir>", "speed": 1.07, "whisper_model": "<ggml file>", "language": "ru",
 "recordings": {"A": {"video": "<file>", "audio": "<mono 48 kHz wav>"}},
 "pieces": "<pieces.json the accepted video was built from; omit for a first build>",
 "cuts": [[from, to]], "mute": [[from, to]],                 // seconds of the accepted video
 "end": [["A", old edge, new edge]], "start": [["A", old edge, new edge]]}  // seconds of the recording
Scenes stay in the seconds of the accepted video: kit/time.ts maps time by time-map.json."""
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

SHORT = 0.6
MIN_PIECE = 0.04


def load(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    out = Path(cfg["out"])
    out.mkdir(parents=True, exist_ok=True)
    return cfg, out


def _near(table, rec, value):
    for r, old, new in table:
        if r == rec and abs(old - value) < 0.02:
            return new
    return None


def edit_pieces(pieces, cuts, ends, starts, mutes, speed):
    """New pieces and the map rows: new start, new end, old start, old end, lead. Pure, so it can be tested."""
    parts = []
    for p in pieces:
        rate = (p["b"] - p["a"]) / (p["to"] - p["from"])
        spans = [(p["from"], p["to"])]
        for x, y in cuts:
            kept = []
            for a, b in spans:
                if y <= a or x >= b:
                    kept.append((a, b))
                    continue
                if a < x:
                    kept.append((a, x))
                if y < b:
                    kept.append((y, b))
            spans = kept
        for a, b in spans:
            if b - a >= MIN_PIECE:
                parts.append({"c": p["c"], "clip": p.get("clip"), "old_a": a, "old_b": b, "a": p["a"] + (a - p["from"]) * rate, "b": p["a"] + (b - p["from"]) * rate})
    out, rows, at, used = [], [], 0.0, 0
    for q in parts:
        was_a = q["a"]
        e = _near(ends, q["c"], q["b"])
        s = _near(starts, q["c"], q["a"])
        if e is not None:
            q["b"] = e
            used += 1
        if s is not None:
            q["a"] = s
            used += 1
        d = (q["b"] - q["a"]) / speed
        shift = (q["a"] - was_a) / speed
        out.append({"from": round(at, 4), "to": round(at + d, 4), "c": q["c"], "a": round(q["a"], 4), "b": round(q["b"], 4), "clip": q["clip"]})
        rows.append([round(at, 4), round(at + d, 4), round(q["old_a"] + max(0.0, shift), 4), round(q["old_b"], 4), round(max(0.0, -shift), 4)])
        at += d
    if used != len(ends) + len(starts):
        raise SystemExit(f"Границ в правках {len(ends) + len(starts)}, на краях кусков найдено {used}: проверьте секунды записи")
    muted = []
    for x, y in mutes:
        r = next((r for r in rows if r[2] <= x < r[3]), None)
        if r:
            lo = r[0] + r[4] + x - r[2]
            muted.append([round(lo, 4), round(lo + y - x, 4)])
    return out, {"rows": rows, "duration": round(at, 4), "mute": muted, "cuts": cuts}


def plan(cfg, out):
    pieces = json.loads(Path(cfg["pieces"]).read_text(encoding="utf-8"))
    new, meta = edit_pieces(pieces, cfg.get("cuts", []), cfg.get("end", []), cfg.get("start", []), cfg.get("mute", []), cfg.get("speed", 1.0))
    (out / "pieces.json").write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
    (out / "time-map.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print("кусков", len(new), "длина", meta["duration"], "глушить", meta["mute"])
    print("короткие куски, прослушать каждый:", [(p["from"], round(p["to"] - p["from"], 2)) for p in new if p["to"] - p["from"] < SHORT])


def build(cfg, out):
    import numpy as np

    speed = cfg.get("speed", 1.0)
    rows = json.loads((out / "pieces.json").read_text(encoding="utf-8"))
    map_file = out / "time-map.json"
    mutes = json.loads(map_file.read_text(encoding="utf-8"))["mute"] if map_file.is_file() else []
    rate, fade = 48000, int(0.006 * 48000)
    ramp = np.linspace(0, 1, fade, dtype=np.float32)
    groups = []
    for p in rows:
        if groups and groups[-1][0] == p["c"]:
            groups[-1][1].append(p)
        else:
            groups.append((p["c"], [p]))
    audio = []
    for rec, part in groups:
        with wave.open(cfg["recordings"][rec]["audio"]) as f:
            pcm = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        for s in part:
            x = pcm[int(round(s["a"] * rate)):int(round(s["b"] * rate))].copy()
            x[:fade] *= ramp
            x[-fade:] *= ramp[::-1]
            audio.append(x)
    joined = np.concatenate(audio)
    for lo, hi in mutes:
        i, j = int(lo * speed * rate), int(hi * speed * rate)
        joined[i:j] = 0
        joined[i - fade:i] *= ramp[::-1]
        joined[j:j + fade] *= ramp
    speech = out / "speech-joined.wav"
    with wave.open(str(speech), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes((np.clip(joined, -1, 1) * 32767).astype(np.int16).tobytes())
    chunks, n = [], 0
    for rec, part in groups:
        for i in range(0, len(part), 20):
            batch = part[i:i + 20]
            ss = max(0, int(batch[0]["a"]) - 1)
            expr = "+".join(f"between(t,{s['a'] - ss - 1 / 120:.4f},{s['b'] - ss - 1 / 60:.4f})" for s in batch)
            script = out / f"select-{n}.txt"
            script.write_text(f"select='{expr}',setpts=N/30/TB,scale=1920:1080", encoding="utf-8")
            target = out / f"part-{n}.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-to", str(int(batch[-1]["b"]) + 2), "-i", cfg["recordings"][rec]["video"], "-an", "-filter_script:v", str(script), "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", str(target)], check=True)
            chunks.append(target)
            n += 1
            print("партия", n, flush=True)
    listing = out / "parts.txt"
    listing.write_text("".join(f"file '{c}'\n" for c in chunks), encoding="utf-8")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-i", str(speech), "-filter_complex", f"[0:v]setpts=PTS/{speed},fps=30[v];[1:a]atempo={speed}[a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "15", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-shortest", str(out / "clean-speech.mov")], check=True)
    for c in chunks:
        c.unlink()
    print("готово:", out / "clean-speech.mov")


def joins(cfg, out):
    rows = json.loads((out / "pieces.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        whole, clip = Path(tmp) / "all.wav", Path(tmp) / "x.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out / "clean-speech.mov"), "-ar", "16000", "-ac", "1", str(whole)], check=True)
        with wave.open(str(whole)) as w:
            rate = w.getframerate()
            for p in rows[1:]:
                w.setpos(int(max(0, p["from"] - 3) * rate))
                data = w.readframes(int(6 * rate))
                with wave.open(str(clip), "wb") as f:
                    f.setnchannels(1)
                    f.setsampwidth(2)
                    f.setframerate(rate)
                    f.writeframes(data)
                res = subprocess.run(["whisper-cli", "-m", cfg["whisper_model"], "-l", cfg.get("language", "ru"), "-mc", "0", "-nt", "-np", "-f", str(clip)], capture_output=True, text=True)
                print(f"{int(p['from'] // 60)}:{p['from'] % 60:05.2f} {' '.join(res.stdout.split())}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("plan", "build", "joins"):
        raise SystemExit(__doc__)
    config, folder = load(sys.argv[2])
    {"plan": plan, "build": build, "joins": joins}[sys.argv[1]](config, folder)

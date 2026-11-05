"""A recording made ready for takes.py, and a whole recording with only its edges trimmed. Called by takes.py."""
import json
import subprocess
from pathlib import Path

HEAD, TAIL = 0.25, 0.4  # seconds of air kept around a whole recording: its first and last words are not clipped
LONGEST = 180  # seconds a recogniser gets at once: a long file makes it loop


def _segments(vad, longest=LONGEST):
    """Spans with speech for the recogniser, each ending in the longest quiet stretch of its last half minute."""
    total, at, rows = len(vad) / 50, 0.0, []
    while total - at > longest + 30:
        lo, hi = int((at + longest - 30) * 50), int((at + longest) * 50)
        best, best_len, run_at, run_len = hi, 0, lo, 0
        for i in range(lo, hi):
            run_at, run_len = (run_at, run_len + 1) if not vad[i] else (i + 1, 0)
            if run_len > best_len:
                best, best_len = run_at + run_len // 2, run_len
        rows.append([round(at, 1), round(best / 50, 1)])
        at = rows[-1][1]
    rows.append([round(at, 1), round(total, 1)])
    return rows


def check_wide(video):
    """recut.py builds a 1920x1080 picture: any other shape would come out squeezed, with nothing to say so later. A phone stores a
    portrait frame as 1920x1080 and a rotation, and it is the rotated frame that ffmpeg gives."""
    found = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation", "-of", "json",
         str(video)], capture_output=True, text=True, check=True).stdout)["streams"][0]
    w, h = found["width"], found["height"]
    if any(abs(int(d.get("rotation", 0))) % 180 == 90 for d in found.get("side_data_list", [])):
        w, h = h, w
    if abs(w / h - 16 / 9) >= 0.02:
        raise SystemExit("Чистая речь делается только для кадра 16:9, здесь {}x{}: {}".format(w, h, video))


def init(video, config_path, out, speed, model, language, prompt, force=False):
    """config.json for a recording: its sound as mono 48 kHz, spans for the recogniser, nothing chosen yet."""
    from takes import loudness

    config_path = Path(config_path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists() and not force:
        raise SystemExit("Конфиг {} уже есть, в нём ваш выбор дублей и края: новый только с --force".format(config_path))
    video = Path(video).expanduser().resolve()
    check_wide(video)
    out = Path(out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "words.json").unlink(missing_ok=True)  # the words of another recording must not stay for `trim`
    audio = out / "speech-48k.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "48000", str(audio)], check=True)
    config = {"out": str(out), "speed": speed, "language": language, "whisper_model": str(Path(model).expanduser()), "prompt": prompt,
              "recordings": {"A": {"video": str(video), "audio": str(audio)}},
              "segments": {"A": _segments(loudness(str(audio)))}, "takes": [], "exclude": [], "trim": {}}
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("конфиг:", config_path, "кусков для распознавания:", len(config["segments"]["A"]))


def _edges(rows, vad):
    """The first and the last word that really have sound: a recogniser writes credits on silence."""
    from takes import settled

    found = []
    for i, w in enumerate(rows):
        a, b = settled(vad, w["a"], w["b"], rows[i - 1]["b"] if i else 0, rows[i + 1]["a"] if i + 1 < len(rows) else w["b"] + 0.45)
        if a is not None:
            found.append((a, b, w["t"]))
    return found


def trim(cfg, out):
    """pieces.json with one piece per recording: from the first word to the last, nothing cut inside. `trim` in the config
    sets the edges by hand, {"A": [from, to]}, in seconds of the recording."""
    from takes import loudness, norm

    raw = json.loads((out / "words.json").read_text(encoding="utf-8"))
    (out / "time-map.json").unlink(missing_ok=True)  # mutes of an earlier plan must not land on this speech
    pieces, script, at, speed = [], [], 0.0, cfg.get("speed", 1.0)
    for idx, (rec, item) in enumerate(cfg["recordings"].items()):
        vad = loudness(item["audio"])
        length = len(vad) / 50
        said = _edges([w for w in raw if w["c"] == rec and norm(w["t"])], vad)
        by_hand = (cfg.get("trim") or {}).get(rec)
        if by_hand is not None and not (len(by_hand) == 2 and 0 <= by_hand[0] < by_hand[1] <= length + 0.05):
            raise SystemExit("trim для {}: нужно [от, до] внутри записи, 0…{:.1f} с; сейчас {}".format(rec, length, by_hand))
        if not said and not by_hand:
            raise SystemExit("В записи {} не найдено речи: задайте края в trim вручную".format(rec))
        a = by_hand[0] if by_hand else max(0.0, said[0][0] - HEAD)
        b = min(length, by_hand[1]) if by_hand else min(length, said[-1][1] + TAIL)
        a, b = round(a * 30) / 30, round(b * 30) / 30
        d = (b - a) / speed
        pieces.append({"c": rec, "a": a, "b": b, "clip": idx, "from": round(at, 4), "to": round(at + d, 4)})
        at += d
        script.append("#{} {}".format(idx, " ".join(w[2] for w in said)))
        print("{}: срезано в начале {:.2f} с, в конце {:.2f} с".format(rec, a, length - b))
        print("  начало:", " ".join(w[2] for w in said[:8]))
        print("  конец: ", " ".join(w[2] for w in said[-8:]))
    (out / "pieces.json").write_text(json.dumps(pieces, ensure_ascii=False), encoding="utf-8")
    (out / "speech-text.txt").write_text("\n".join(script), encoding="utf-8")
    print("кусков", len(pieces), "длина готового ролика", round(at, 1))

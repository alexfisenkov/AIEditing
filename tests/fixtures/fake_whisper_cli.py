"""Stand-in for whisper-cli: checks the arguments it needs and writes `<prefix>.json` like whisper.cpp -oj."""
import json
import sys
from pathlib import Path

args = sys.argv[1:]
opts = {args[i]: args[i + 1] for i in range(len(args) - 1) if args[i].startswith("-")}
wav = Path(args[-1])
for flag in ("-m", "-l", "-of"):
    if flag not in opts:
        sys.exit("missing {}".format(flag))
if wav.suffix != ".wav" or not wav.is_file():
    sys.exit("expected a wav file, got {}".format(wav))
if not Path(opts["-m"]).is_file():
    sys.exit("model not found")
result = {"result": {"language": opts["-l"]}, "transcription": [
    {"offsets": {"from": 0, "to": 120}, "text": ""},
    {"offsets": {"from": 120, "to": 480}, "text": " Привет"},
    {"offsets": {"from": 500, "to": 900}, "text": " э-э"},
    {"offsets": {"from": 1000, "to": 1300}, "text": " мир."},
]}
Path(opts["-of"] + ".json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

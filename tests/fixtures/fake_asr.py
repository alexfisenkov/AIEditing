"""Stand-in for a user's own recogniser: `fake_asr.py <media> <language> [out.json]`."""
import json
import sys
from pathlib import Path

media, language = Path(sys.argv[1]), sys.argv[2]
if not media.is_file():
    sys.exit("no such media: {}".format(media))
result = {
    "language": language,
    "words": [
        {"word": " Привет", "start": 0.10, "end": 0.42},
        {"text": " ", "start": 0.42, "end": 0.50, "type": "spacing"},
        {"text": "э-э", "start": 0.50, "end": 0.90},
        {"text": "мир", "start": 1.00, "end": 1.30},
    ],
}
payload = json.dumps(result, ensure_ascii=False)
if len(sys.argv) > 3:
    Path(sys.argv[3]).write_text(payload, encoding="utf-8")
else:
    sys.stdout.buffer.write(payload.encode("utf-8"))

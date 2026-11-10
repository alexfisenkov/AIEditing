# Frames, face geometry, OCR and word timing

Use this page when an edit needs a measured crop, a moving face/window, screen text or speech
timestamps. These measurements answer different questions: a face box is not a person's identity,
OCR is not a transcript, and word timestamps are not guaranteed cut points.

Run Python blocks with `capabilities --json`'s `executables.python` and the installed skill folder
as the working directory; that makes this skill's `runtime` importable. Use the returned executable
paths for CLI commands. In API blocks, set `frame_path`, `sample_wav` and `output_png` to files in
the working/issue folder, and `skill_dir` to the installed skill. Never save media inside the
installed skill directory. Start with a representative frame or a 10–30 s local excerpt. The
recipes here preserve the source and do not edit a format profile.

## YuNet and OpenCV: from a box to a usable crop

For a frame already extracted by the kit's `frames` command, use the installed detector:

```python
from pathlib import Path
from runtime.look.faces import yunet
faces = yunet(threshold=0.7)(frame_path)
# Each result: x, y, w, h in displayed-image pixels, plus score; sorted by score.
```

The score is detector confidence, not permission to use a particular subject. Check whether the
box is the live speaker, a second participant, a poster or a face on a monitor. With several
plausible faces, choose the intended person from actual frames; do not switch subjects because
another score becomes marginally larger.

When using `cv2.FaceDetectorYN` directly, call `setInputSize((width, height))` for the actual image.
OpenCV arrays are BGR; Pillow/RVM RGB data must be converted explicitly. The detector's raw result
has 15 columns: box, five landmarks and confidence. AIEditing's wrapper intentionally exposes only
the box and score. It decodes image bytes with `np.fromfile`/`cv2.imdecode` for Unicode Windows paths.

Keep coordinate systems named: original stored frame, displayed/rotated frame, analysis proxy,
final composition. Multiply proxy coordinates by the inverse scale before cropping the source.
If rotation is 90/270 degrees, displayed width/height are exchanged; do not apply the rotation twice.
Add headroom and the target aspect ratio around the face instead of cropping exactly to its box.

For motion, sample a few positions per second, reject low-confidence jumps, then smooth within one
shot and interpolate at render FPS. Reset on cuts. A lost/ambiguous track should hold a verified
framing or show the complete picture, not pan to an unrelated face. Inspect entrance, fastest
movement, occlusion and exit at full size. Existing `runtime.look.track.track_region` is a bounded
template-based region tracker used for blur; it is not a general identity tracker and has no
occlusion recovery guarantee. Reinitialize it after a cut or a major appearance change.

## Tesseract: screen text and candidate secret regions

1. Extract a readable frame at the original text scale. Crop the relevant UI/text region and record
   its offset so OCR boxes can be translated back. Upscaling or contrast adjustment can help a
   small preview, but compare with the original before accepting a character.
2. Run the returned Tesseract executable with `--list-langs`. `eng` and `osd` do not include Russian;
   choose `rus+eng` only after the corresponding traineddata has actually been installed.
3. Use page segmentation appropriate to the crop: `--psm 7` for one line, `6` for one block, `11`
   for scattered UI labels. Try the normal crop first; then compare a cleaned variant if needed.
4. Request TSV for word boxes/confidence; preserve the crop offset and any resize factor.

For an English one-line crop, the argument list is:

```python
import subprocess
args = [tesseract_executable, "crop.png", "stdout", "-l", "eng", "--psm", "7", "tsv"]
done = subprocess.run(args, capture_output=True, text=True, check=True)
```

Treat OCR text and confidence as candidates. Visually check names, digits and important buttons;
an OCR miss does not prove a secret is absent. For redaction, inspect the marked region through
the entire exposed interval, including moving windows and transitions; audio and subtitles need
their own secret checks. Do not put detected secret values into reports or screenshots.

## whisper.cpp: a transcript that can support an edit

Use the recognizer chosen by the workshop/profile. For local recognition, the provider extracts
mono 16 kHz PCM and uses `-ml 1 -sow -oj`, producing short word-oriented segments. Resolve the
installed model and private Windows executable through AIEditing, rather than guessing a path.
The local model is `ggml-large-v3`; `asr.model` or `AIEDITING_WHISPER_MODEL` can name an explicit file.

In an active workshop, `ae.py hear <draft skill> <video>` prints what that draft's recognizer hears.
For an isolated diagnostic outside a workshop, use `runtime.asr.transcribe` with an explicit local
provider config, then save a local result. Loading the model is a real resource cost; first inspect
the available memory and use a short representative excerpt.

```python
from pathlib import Path
from runtime.asr import transcribe
result = transcribe(sample_wav, {"provider": "whispercpp", "language": "ru"})
for word in result["words"]:
    print(word["start"], word["end"], word["text"])
```

Only print word text from an excerpt already known to be free of secrets. In a redaction task,
report the type/time of an exposure and keep its actual value out of command output and reports.

Hear the normal-speed source around every proposed inside-speech seam. Very short words, fillers,
false starts and long silences can have missing or inaccurate timestamps. Local token/word timing
is experimental upstream; a second recognizer pass can also make mistakes. If uncertain, keep the
word and adjust the seam by listening instead of trusting the largest confidence-looking number.
Measure/rehear after cutting, before any speed change; apply the chosen speed once and carry its
time mapping into subtitles. A final `.srt` correction goes through the existing words/corrections
flow so it is not overwritten on the next run. Keep the glossary's actual terms and spelling.

If recognition loops in silence, compare the chosen excerpt with `max_context=0` and check the
result; this is a diagnostic option, not a universal quality improvement. Recognition text must
not invent an unheard sentence. A requested external recognizer uses its existing authorization;
do not switch to paid/uploaded inference as an invisible fallback.

## Pillow and NumPy: measured PNG layers

For static plates or captions, prefer the format kit's own design renderer. A one-off PNG uses
RGBA, the design's actual font file and measured text bounds. `textbbox`/`multiline_textbbox` replace
old `textsize`-based guesses. Fit the complete text inside the safe rectangle by wrapping, shortening
with the person's meaning intact, or reducing type deliberately; drawing outside the canvas is
silently clipped by Pillow.

```python
from PIL import Image, ImageDraw, ImageFont
import sys
sys.path.insert(0, str(skill_dir / "tools"))
from recipe_lib.common import output_file
canvas = Image.new("RGBA", (800, 200), (0, 0, 0, 0))
font = ImageFont.truetype(str(skill_dir / "design/chrome-graphite/fonts/Onest.ttf"), 48)
draw = ImageDraw.Draw(canvas)
box = draw.textbbox((0, 0), "A short label", font=font)
draw.text((32 - box[0], 32 - box[1]), "A short label", font=font, fill=(255, 255, 255, 255))
with output_file(output_png) as staged:
    canvas.save(staged, format="PNG")
```

Use this only as an API sample; colours, canvas, label and placement come from the chosen design.
NumPy masks must have a declared shape, scale and finite values: RVM input is float32 RGB NCHW in
0–1, while a PNG alpha channel is typically 0–255. Do not multiply an already premultiplied edge a
second time. Inspect the PNG on light and dark backgrounds and in the final encoded video.

## Sources and local contracts

- [OpenCV 5 FaceDetectorYN: create, input size and result columns](https://docs.opencv.org/5.0/main_modules/objdetect_dnn_face.html).
- [Tesseract command line: languages and TSV](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)
  and [input quality/segmentation modes](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html).
- [whisper.cpp word-timestamp documentation and CLI](https://github.com/ggml-org/whisper.cpp#word-level-timestamp-experimental);
  pinned 1.9.5 `whisper-cli --help` and local `runtime/asr/whispercpp.py` verify the flags used here.
- [Pillow ImageDraw bounds and clipping](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html).
- Local contracts: `runtime/look/faces.py`, `runtime/look/track.py`, `runtime/asr/contract.py`,
  `runtime/asr/whispercpp.py`; current profile glossary/corrections and time ownership remain authoritative.

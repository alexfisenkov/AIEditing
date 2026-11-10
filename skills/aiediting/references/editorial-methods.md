# Editorial methods for a local montage

Use for cuts, takes, B-roll, captions, colour, sound or several cameras. A library
can locate technical candidates; the editor decides what the viewer needs to
understand. The installed toolbox is finite. Run `ae.py capabilities --json`
to inspect this machine, then verify the chosen route on the source and result.
Do not turn a missing catalog step into a categorical refusal or call a detected
event an accepted edit.

## 1. Make a source map

Before changing picture, use `ffprobe` or AIEditing's source inspection to
record duration, fps, frame size, rotation and audio tracks. Sample the
beginning, middle, end, every camera or screen layout, and any suspected cut.
Note the source paths and their roles without copying private media into a
public skill. A multitrack recording needs a declared speech/master audio
track; a camera's scratch audio can be an alignment reference without becoming
the final sound.

```bash
python3 "<skillDir>/tools/ae.py" capabilities --json
ffprobe -v error -show_entries stream=index,codec_type,codec_name,width,height,r_frame_rate -show_entries format=duration -of json source.mp4
```

PySceneDetect 0.7.3 can produce **shot-boundary candidates**. Its official
[examples](https://www.scenedetect.com/docs/latest/examples.html) show
`detect(path, AdaptiveDetector())` returning `(start, end)` timecode pairs,
or the `scenedetect -i video.mp4 list-scenes` CLI for a CSV. A cut detector
does not identify the best take, a meaningful sentence or a legal asset.
Review false positives from camera motion and false negatives from gentle
transitions. Keep the scene list as evidence, not an automatic delete list.

Run the following API examples inside AIEditing's private Python after
`ae.py setup`; they were exercised on a generated two-colour video, a
one-line subtitle and a one-second pulse in a temporary folder. They are
analysis and file-conversion operations, not a finished montage:

```python
from scenedetect import AdaptiveDetector, detect
shots = [(start.seconds, end.seconds)
         for start, end in detect("source.mp4", AdaptiveDetector())]

import soundfile as sf
import librosa
mono_samples, sample_rate = sf.read("speech-mono.wav")
candidate_events = librosa.onset.onset_detect(
    y=mono_samples, sr=sample_rate, units="time")

import pysubs2
captions = pysubs2.load("approved.srt", encoding="utf-8")
print(len(captions.events))  # inspect; use subtitle-convert for a guarded new output file
```

`candidate_events` are acoustic onsets, not spoken words or approved SFX
cues. The WAV must be mono for this sparse onset example. Inspect the
converted subtitle text and render before accepting its appearance. See
librosa's [onset API](https://librosa.org/doc/main/api/generated/librosa.onset.onset_detect.html)
and pysubs2's [save API](https://pysubs2.readthedocs.io/en/latest/api-reference.html).

## 2. Lock meaning and timing before decoration

1. Read or hear the full passage. Mark the thought, qualification, example and
   payoff of each section. A repeated sentence may be a correction, a rhetorical
   return or a new detail; compare meaning before dropping it.
2. Build a source-time edit decision list: `source file`, `in`, `out`,
   `keep/drop`, `reason`, `speaker`, `audio master`. Preserve a small
   lead/tail around words. Silence is a candidate for shortening; a word
   inside a “silent” detector window is a reason to revise the cut.
3. After assembling the clean speech, derive the new final-time map and
   transcription from that file. Do not put captions or graphics on source
   times after a ripple edit. AIEditing's `verify_words` and `drift_ms`
   help catch loss and sync; listen across every tight join yourself.
4. Lock the rough edit before building expensive overlays. A change to the
   final-time map invalidates downstream word cues, graphics, captions and
   sound effects.

The owner's project notes about its video-use checks found that word timestamps may be
estimated or omit short words; that is a reason to inspect uncertain joins,
not a benchmark for every recogniser or video. A second ASR pass does not
replace hearing the final audio. Paid or remote recognition is chosen under
the separate ASR permission boundary.

## 3. B-roll with a reason

Make a shot plan tied to one claim or action per insert. Prefer a real product
screen, demonstration or object the person supplied over a generic illustration.
An insert can prove a point, reveal a process, conceal an accepted picture
splice or carry a specific reaction. If it provides none of these, keep the
speaker. Do not infer footage ownership, licence, student identity or a product
state from a file name.

For simultaneous A-roll and B-roll, make the overlay span explicit: both
sources start and end at known final-time frames; outside that span the speaker
returns to the intended full layout. Mute or deliberately mix B-roll scratch
audio before making captions. A split layout that persists after the B-roll
ends leaves an empty half-frame. This principle is adapted from the supplied
UGC editing material; its Palmier `apply_layout` command is **not** an
AIEditing or FFmpeg command.

## 4. Multicam: synchronization and picture program are separate

Inventory every camera and microphone. Find a common clap, timecode or
correlated audio event, then verify alignment at the start **and end**; a
matching first frame alone does not rule out drift. Decide which source is
the clean speech track. For different speakers, hold the active speaker
through a turn and use a wide shot or layout when reactions overlap. For
two cameras of one speaker, keep a primary angle and use the second for a
motivated detail, reaction or accepted cut. Rebuild picture switch times
from the *post-cut* audio map so a brief alternate angle does not bridge a
word splice.

AIEditing currently has `drift_ms`, not a general multicam timeline.
Compose a small verified segment with the available local tools or an
actually connected editor, then inspect the resulting frame sequence and
audio. The supplied multicam skill contributes this decision method, not
an assumed Palmier MCP installation.

## 5. Captions, colour and sound serve the edit

- **Captions:** settle the wording and glossary after the cut. Choose one
  treatment suited to the purpose: quiet readable text for teaching or
  interviews; an active-word emphasis for a fast short only when it helps
  comprehension. Check the first, densest and last captions at actual
  output size, over the face and any platform controls. A local `pysubs2`
  pass can read or convert SRT/ASS, but conversion does not prove visual
  placement or word accuracy; see its [format and API guide](https://pysubs2.readthedocs.io/en/latest/index.html).
  The supplied Palmier presets are design references, not portable API
  arguments.
- **Colour:** normalize exposure and white balance on representative shots,
  match neighbouring shots, then apply a look or LUT. Compare skin and
  highlights before/after at the same frame. Use an available FFmpeg filter
  or another confirmed local tool; AIEditing does not yet have a general
  colour-grading step. A LUT with unknown source or a visually pleasing
  screenshot is not a calibrated grade.
- **Sound:** keep speech intelligible first. Measure and listen to the
  exported file, not only an intermediate WAV. Clean steady noise on a
  sample and check that consonants and room tone survive. Align sound
  effects to the event they support, use one consistent sound language,
  and avoid covering the word that carries the message. SoundFile and
  librosa can help measure PCM and timing; neither chooses the edit or
  completes a mix. Music and SFX need a known source and permitted use.

## 6. Acceptance through the actual file

Use a representative short edit to prove timing, framing, caption style,
sound and any new tool before processing a long source. For graphics,
read [graphics-and-compositing.md](graphics-and-compositing.md); for a
matte, read [background.md](background.md). Then inspect:

- **Still frames:** first visible frame, entrances, filled states, scene
  boundaries, captions at maximum density, face/background edges and end.
- **Motion:** play every join and a continuous stretch through each
  treatment. Look for flicker, jitter, jumps, drifting layouts and
  mismatched camera/audio changes.
- **Sound:** hear the original and final at the same places, especially
  words near cuts, transitions and the end; check the intended track
  remains present after muxing.
- **Technical:** probe codec, dimensions, fps, duration, audio and alpha
  where requested; decode the entire output. A green command exit or
  contact sheet is one piece of evidence, not a viewer acceptance.

Write the chosen source ranges, visual reasons, used local assets, tool
versions and any unverified places into the issue report. Keep the
originals. Upload, sending and publication remain separate actions.

The method adapts the supplied motion-studio prompt, motion/B-roll and
sound skills, Palmier editorial skills and the project's own
`overlay-kit`. Exact local provenance and excluded materials are in
the private engineering ledger. None of their code or sample media is
copied into this document.

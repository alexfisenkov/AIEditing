# Graphics and compositing from spoken meaning

Use when the edit needs titles, diagrams, real screens, animated inserts or foreground
compositing. Read the complete spoken passage before choosing a visual. A good insert
answers what the viewer needs to *see* at that word; an empty phrase need not receive
an effect. The scene plan is editorial data. Rendering only proves that code ran.

## Pick the smallest visual route

| Need | Route | Check before expanding |
|---|---|---|
| One list, count, step or other bounded insert beside a screen | AIEditing `animations` step on pinned HyperFrames 0.9.28 | Place it at the phrase that introduces the items, keep it readable, and inspect its first/last frame. Reuse the format's design. |
| Graphics throughout a talking-head recording, speaker moving between layouts, real product screens | The bundled Remotion 4.0.542 `overlay-kit` through a format's `graphics` step | Confirm the input video, final word times, tokens, available assets and face track before writing scenes. |
| A long horizontal video re-edited as vertical clips | `reedit` and `overlay-kit/vertical.md` | Rebuild each selected clip's graphics and safe areas; a wide screen shrunk into 9:16 is not automatically legible. |
| A plate or animation behind a filmed person | `behind_head` plus an actual chosen graphic step; see `background.md` | The matte and graphic need matching time and frame geometry; inspect hair and foreground continuity. |

HyperFrames' [v0.9.28 release](https://github.com/heygen-com/hyperframes/releases/tag/v0.9.28)
and [rendering guide at that tag](https://github.com/heygen-com/hyperframes/blob/v0.9.28/docs/guides/rendering.mdx)
describe its local render and alpha routes. They do not make AIEditing's format
choices or replace a review of the composited output. Node.js is the runtime
for HyperFrames and Remotion, not an independent montage skill: installing
Node does not select shots, write a scene plan or approve a render. Remotion's official
[`<Sequence>`](https://www.remotion.dev/docs/sequence),
[`interpolate()`](https://www.remotion.dev/docs/interpolate) and
[`still` command](https://www.remotion.dev/docs/cli/still) explain frame-based timing
and inspection; AIEditing's kit defines its own scene files and seconds-of-video contract.

## Plan shots before code

1. Make a table: `from–to` in the *finished input video's* seconds, exact spoken
   phrase, visual claim, source asset, intended layout, first readable frame and exit.
   A person saying “three steps” can earn a list; a personal or emotional sentence
   may be stronger with an unobstructed face. Do not infer product screens, numbers,
   testimonials or names from a generic template.
2. For each scene, choose one main visual hierarchy: speaker, real demonstration,
   diagram or text. A short title can label a real screen but should not obscure it.
   Keep adjacent scenes visually distinct; show a real slide whole before zooming
   into its detail. Check the face position on the actual footage, including when
   the camera is a small circle in a screen recording.
3. Bind each appearance to a word or phrase boundary from `слова-таймкоды.txt`
   or `raw/words.txt`, then listen at that moment. ASR timing is an estimate,
   especially near cuts or a speed change. The kit's `useT()` and scene
   `{from, to, C}` use seconds of `public/clips/source.mp4`; a marker time map
   needs the kit's mapping instead of hand-shifting every cue.
4. Give the plan a motion arc: setup, main change, readable held state, exit.
   Ease an entering element toward rest and let the viewer read it before
   another event. Stagger related items when it conveys order; avoid motion
   everywhere at once. These are editorial choices adapted from the supplied
   motion-design materials, not automatic timing constants.

The kit's local [README](../overlay-kit/README.md), [scene brief](../overlay-kit/brief-template.md)
and `examples/seg-a.tsx` are the implementation contract. A segment exports
`scenes: Scene[]` with `{from, to, C}` and `cues: Cue[]`; its paired
`layouts-a.ts` exports `LAYOUTS_A` as `[second, layout]`. Use its
`At`, `Appear`, `Screen`, `WorkFrame` and token helpers after reading their
current signatures. The example demonstrates the file shape; do not copy its
content, colours or fictitious numbers into a person's video.

For a chart, record the exact supplied values, units, labels and axis assumptions before
animating. Check that final labels and bar/area ratios agree with those values; animation must
settle on the actual data, not an attractive invented count. Mark authorized illustrative data
as illustrative, and keep it out when the person asked for factual evidence. For a visual
reference, split the brief into **moves** (trajectory, order, easing, holds) and **look**
(type, palette, surfaces). Say which part is borrowed and which stays with the requested
design; copying a movement does not authorize copying a brand or its assets. These two
checks adapt the supplied animated-chart and reference-to-motion materials.

## A checked local overlay pass

If a format already produced an approved base edit and its checked word file, use those.
For a one-off graphics request with no format, take the exact approved video as `base_video`;
if the request includes cuts, first assemble a separate approved base via the editorial EDL.
Transcribe **that base**, not an earlier uncut source. Set `skill_dir`, `base_video` and a new
`words_file` inside the issue folder, then export the provider's word list to the kit's
`seconds word` format:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(skill_dir))
sys.path.insert(0, str(skill_dir / "tools"))
from runtime.asr import transcribe
from recipe_lib.common import output_file
transcript = transcribe(base_video, {"provider": "whispercpp", "language": "ru"})
lines = ["{:7.2f} {}".format(w["start"], w["text"].strip().replace("\n", " "))
         for w in transcript["words"] if w["text"].strip()]
if not lines:
    raise ValueError("No words: inspect the actual source before planning graphics")
with output_file(words_file, sources=(base_video,)) as staged:
    staged.write_text("\n".join(lines) + "\n", encoding="utf-8")
```

Use the already authorized recognizer if different; do not silently upload speech as a
fallback. Listen at the first/middle/last words and scene cues and confirm their seconds
belong to the chosen base. A short preview extracted from the base has its own zero; its
word file cannot stand in for a full-length transcript.

For a starting design, `skill_dir / "design/chrome-graphite"` contains example `tokens.json`
and fonts usable by the kit. Declare it an example; use the person's provided design when
available and convert it to the documented token schema. The `prepare` route here expects
16:9 video with audio (or the supported separate speech input); select the kit's documented
vertical/re-edit path for a portrait task rather than silently cropping it into this route.

Choose a **new empty** absolute work folder for this issue. Do not run `prepare` over an
unrelated/existing project: scaffolding can overwrite files. On a fresh dependency environment
it may run pinned npm/browser downloads; announce that under the existing local-tool setup
authorization. Shared verified dependencies are reused when their lock matches. `--no-install`
is only for an intentionally prepared folder with verified local dependencies, not an offline
shortcut for an unprepared new folder.

For direct `overlay.py` commands, use the quoted private Python executable from
`capabilities.executables.python` in place of the illustrative `python3` below. This keeps
Pillow/OpenCV and the selected runtime consistent. These commands
are supported by `overlay.py --help` in the bundled kit. After `prepare`,
write the scene and layout files from the approved plan and the kit's brief;
then use `frame`, `draft` and the final checks:

```bash
python3 "<skillDir>/overlay-kit/tools/overlay.py" prepare base.mp4 /absolute/work --words words.txt --design /absolute/design
# Write /absolute/work/src/scenes/seg-a.tsx and /absolute/work/src/data/layouts-a.ts from the brief.
python3 "<skillDir>/overlay-kit/tools/overlay.py" frame /absolute/work 5 13.7
python3 "<skillDir>/overlay-kit/tools/overlay.py" draft /absolute/work
python3 "<skillDir>/overlay-kit/tools/overlay.py" empties /absolute/work/out/draft.mp4
```

The existing kit's `final` can replace its named destination. For a one-off method, place
its render in the guarded staging path below, never directly over an input or previous
render. Set `work`, `final_output` and `python_executable` to the selected paths; the output
must be a new `.mp4`. The shared output helper refuses an existing result/source alias:

```python
import subprocess
with output_file(final_output, sources=(base_video,)) as staged:
    subprocess.run([python_executable, str(skill_dir / "overlay-kit/tools/overlay.py"),
                    "final", str(work), str(staged.parent), staged.name], check=True)
```

After this command succeeds, run `sheets` on the actual final file into a new sheet folder
and `sync` against the exact base. Keep draft/final logs with the issue. For a revision, retain
the earlier output and select a fresh versioned name; do not substitute the source path.

Before the draft, inspect stills at every scene entrance, one filled state, one
exit and each layout change. Look for a bare stage after the speaker moves, text
outside the safe area, a face covered by graphics, wrong real-screen coordinates
and a repeated screenshot. A visual still does not verify audio; a draft does not
verify full-resolution text. After the final, inspect contact sheets, decode and
listen to the actual output. The kit's `final` and `sync` check audio offset and
duration; a nonzero result is a failed deliverable.

For a bounded HyperFrames insert chosen in a workshop profile, the supported
repair and probe route is:

```bash
python3 "<skillDir>/tools/ae.py" setup --steps animations
python3 "<skillDir>/tools/ae.py" trial <draft-skill> source.mp4 --start 10 --duration 15
```

The draft skill and workshop state must already exist for `trial`. A standalone
HyperFrames project requires its own project specification; do not invent an
AIEditing CLI that creates one. Choose transparent MOV or another alpha-capable
intermediate only when the next compositor can read it. A finished H.264 MP4
normally has no usable transparency. Verify the foreground/background layer
order on the final file, not on a JSX preview.

## Captions and real B-roll in the composition

The supplied caption-preset materials show useful *selection* principles:
choose a restrained treatment for a lesson, a stronger active-word treatment
only when the pacing asks for it, and place every caption against the actual
face and platform controls. Adapt the design to this kit's tokens and text
renderer; a Palmier `add_captions` configuration is not a Remotion API.
Correct transcription and brand terms before burning text into the picture.

Real B-roll should prove a statement, reveal a process, cover an intentional
cut or carry a specific emotional beat. Use assets the person supplied or
explicitly authorized. Preserve their source and licence. A screenshot or
recording of a product must show the actual interface at the relevant time;
never generate a plausible but false screen. A motion graphic can explain
what no real footage can show, but should not masquerade as evidence.

The adapted ideas came from the locally supplied motion-studio prompt, motion
principles, B-roll and caption skills. Their versions and exclusions are
recorded in the private engineering source ledger. No external code pack,
private brand asset or sample video is bundled here.

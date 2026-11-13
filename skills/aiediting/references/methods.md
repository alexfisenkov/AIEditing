# Tool methods: choose, execute, judge

Read this index when a requested operation needs more than a format's existing native steps.
Open only the relevant page(s), then return to the active workshop phase. A library's presence
is not a visual decision or a finished edit. The separate installed format skills are not
modified merely because the parent learns a method.

## Start with the actual environment and source

1. Run `python3 "<skillDir>/tools/ae.py" setup --check`; repair the requested local dependencies
   with the existing setup flow if necessary. Use `capabilities --json`'s executable paths and
   filter inventory. Generic `python3`/`ffmpeg` in another shell may select a different environment.
2. Inspect a local source's duration, streams, frame orientation, FPS, colour tags and a few
   representative frames. Name whose seconds a plan uses: original, cut intermediate or final.
3. Choose a native pipeline/kit route or a method below. Make a short probe, measure the relevant
   invariant and inspect/hear what a metric cannot judge. Expand to the requested duration only
   after the probe earns it. Preserve the original and keep outputs in the work/issue folder.

| Need | Read | Executable route or native contract |
|---|---|---|
| Shot boundaries and detector tuning | [scene-analysis.md](scene-analysis.md) | `recipes.py scenes`; candidates in source seconds, not a best-take selector |
| Audio features, recorder offset and drift | [audio-analysis-and-sync.md](audio-analysis-and-sync.md) | `audio-report`, `audio-sync`; bounded measurements, no automatic source shift |
| Noise, voice level, ducking, tempo/pitch | [audio-processing.md](audio-processing.md) | Checked FFmpeg filters and two-pass measurement; apply speed once |
| SRT/ASS/VTT, retiming and styled burn-in | [subtitles.md](subtitles.md) | `subtitle-convert`, `subtitle-burn`; preserve styles or restyle explicitly |
| Shot matching, LUTs, scopes and stabilization | [color-and-stabilization.md](color-and-stabilization.md) | FFmpeg colour recipes and two-pass `stabilize` on one continuous cut |
| Human/video, still/object, chroma, alpha | [background.md](background.md) | Existing `ae.py background` and `image-cutout`; inspect temporal/edge behaviour |
| Face boxes, region tracks, OCR, word times, PNG | [vision-and-transcription.md](vision-and-transcription.md) | Existing look/ASR/render APIs; confidence and coordinate/time ownership |
| HyperFrames inserts, Remotion, layers and motion | [graphics-and-compositing.md](graphics-and-compositing.md) | Existing overlay kit and renderer methods, still → draft → final |
| B-roll, multicam programme, captions and sound decisions | [editorial-methods.md](editorial-methods.md) | Adapted supplied-skill principles; source-based edit plan, then local composition |
| Own footage, a library, gentle cuts and a plan of angles | [editorial-methods.md](editorial-methods.md) | `ae.py library`, the steps `broll`, `angles`, `params.cleanup`; only when the person chose them |
| Codec/decode, sync, black/freeze diagnostics and VMAF | [technical-quality.md](technical-quality.md) | `quality` only for explicitly aligned same-content inputs; human inspection remains separate |

## The checked recipe launcher

```text
python3 "<skillDir>/tools/recipes.py" --help
python3 "<skillDir>/tools/recipes.py" <method> --help
```

This separate launcher selects AIEditing's private Python and process-local full FFmpeg path.
It does not start the workshop, change any format profile or install a package. Analysis commands
print JSON and can save an optional report; finishing commands write the requested new artifact.
Existing outputs require `--replace`; sources and their hard-link aliases remain protected.
On hard-link-capable volumes the final new-name placement is atomic. A volume such as
exFAT may require an exclusive copy after validation; do not use that artifact until the
command exits successfully. Failed copies clean up their own partial result. Never treat
the mere appearance of a filename as a completion receipt.
Fenced `bash` examples use Bash syntax; on Windows use a single-line form or Python
argument lists, not literal backslash continuations. Use `python3` where available, or
the returned private Python executable when a host has a different launcher.
Read each method's flags: they are commands of `recipes.py`, not new native `ae.py` step names.

Analysis output is evidence for a decision. Do not render an EDL solely because a threshold fired,
retime a camera merely because one correlation peak exists, or grade unrelated scenes to maximize
VMAF. Keep the editorial plan and its time mapping separate from measurements and output files.

## Turn a successful probe into a format only on a format task

For a one-off method, retain its inputs, settings, inspected seconds and limitations in the issue
report. When the person later asks to make it repeatable, use the normal AIEditing refinement/build
flow: chosen steps, profile/schema, runtime or self-contained method, tests, trial and backup. This
knowledge update itself does not rebuild or change any existing `монтаж-*` format.

Sources and coverage are recorded in [method-sources.md](method-sources.md). The official tool API
and the pinned local code take precedence over a supplied skill's unavailable application/MCP call.

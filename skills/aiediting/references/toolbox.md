# Editing toolbox beyond the catalog

Read when a requested montage operation is absent from a preset or `catalog/steps.json`.
The catalog is the set of repeatable AIEditing steps, not a list of every edit an agent can make.
Detailed methods and checked executable examples are indexed in [methods.md](methods.md).
First inspect the source and the installed local tools. Use
`python3 "<skillDir>/tools/ae.py" capabilities` (or add `--json`) to see this machine's
actual FFmpeg filters and available tools; `setup --check` checks the complete maintained
toolbox. A listed tool or filter is a starting point, not proof that it works on this source
or meets the visual standard.

The JSON also gives `executables` and the full `ffmpeg_filters` list. Use those exact executable
paths for one-off commands: setup changes its own process environment, not the user's global PATH.
The full FFmpeg build includes ASS subtitles, VidStab, Rubber Band and VMAF; inspect the available
filters and the chosen tool's own documentation before composing a method.

## Choose an executable route

| Request | AIEditing now | Route when the requested result needs more |
|---|---|---|
| Cuts, pauses, retakes | `speech_spans`, `cut_spans`, `verify_words`; format methods can select takes | PySceneDetect can identify scene boundaries for a source-time edit list; it does not choose the best take. Assemble with FFmpeg or the format kit. Hear each join and check that intended words remain. |
| ASR and subtitles | Local whisper or the chosen ASR, `write_srt`, `overlay_png`, glossary and correction flow | pysubs2 can read or convert local SRT/ASS; compose word-level or animated captions in Remotion/another local renderer. Verify timing, spelling and safe areas on actual frames. |
| Audio cleanup, mix and SFX | Native `loudnorm` and music from an authorized library; explicit cleanup recipes in [audio-processing.md](audio-processing.md) | The existing `params.denoise` flag alone does not perform noise reduction. Use a verified FFmpeg cleanup route. SoundFile/librosa measure PCM audio, rhythm and offset; listen to speech and transitions after processing. Use sound assets only from an authorized source. |
| Color, matching and LUTs | No general color-grading step | Measure representative frames, use verified FFmpeg color tools or a locally available editor, compare shots and inspect skin, clipping and gamut. A LUT path and its rights must be known. |
| Reframe, transforms and speed | `detect_layout`, `vertical`, `motion`, profile speed and `export_platforms` | Compose crop, scale, pad, rotation or time changes with available FFmpeg filters or Remotion. Check framing, audio pitch, sync and subtitle times. |
| Stabilization and tracking | No general-purpose step | Check `capabilities` for a suitable installed filter or select a real local tracker/stabilizer; install checked requirements in an isolated environment. Test a short moving segment before processing the whole video. |
| Green screen, natural background and alpha | `background` supports local human matting and a chroma-key mode; `behind_head` places a foreground over graphics; see `background.md` | Inspect green-screen spill and edges. For arbitrary objects or difficult occlusions, select a specialist tool and validate a preview; human matting alone does not solve every mask. |
| Still-image background | `ae.py image-cutout <source> <output.png>` uses local rembg with the pinned MIT BiRefNet General Lite model | Inspect the alpha edge and details on the actual image. This route is for stills; it does not provide general object tracking through video. |
| Transitions, overlays and visual layers | `plate`, `overlay_png`, `animations`, `graphics`, `motion`, `behind_head` | Compose with FFmpeg or Remotion after checking available filters/assets. Review transition boundaries and whether text covers important picture. |
| Multicam and sync | `drift_ms` checks output sync; AIEditing has no general multicam timeline | Inspect every camera and audio source, align them by a verified reference, build an edit plan, then assemble locally. A Final Cut or Palmier route is optional only if its tools are actually available in this session. |
| B-roll and story structure | `reedit` and format methods cover specific editorial paths | Build a shot/word plan, use user-provided footage and local FFmpeg/Remotion composition, then review meaning and continuity. AIEditing has no universal B-roll selector. |
| Motion graphics and complex effects | HyperFrames animated inserts and Remotion graphics kit | Build a bounded local composition and render a short probe. A requested 3D, particle or tracking effect may need another verified library and machine resources. |
| Codec, platform export and QC | `export_platforms`, `drift_ms`, `verify_words`, pipeline reports | Check local encoder support with FFmpeg, choose output settings for the target, inspect metadata and decode, then watch and hear the final file. Upload and publication remain separate actions. |

## For an operation outside a native step

1. Identify the exact result, source footage, target format and acceptance check. Inspect a few
   frames and a representative segment. Preserve the original.
2. Run `capabilities` and check the tool's documentation, version, licence, platform requirements
   and resource cost. Prefer the existing local toolkit. If needed, install a real tool in an
   isolated environment and record where it came from. A request to make the edit authorizes
   its local dependencies; announce heavy downloads together and continue without a question
   for every package. Do not use paid inference, upload media or expose keys without the
   person's separate authorization.
3. Make a short probe on the person's own footage, inspect the video and audio, then process the
   full duration. Check the final output independently of the command's exit code.
4. For a one-off edit, record the method and limitations in the result. If it should be repeatable
   for later formats, extend the catalog, profile contract, runtime and tests, and verify the
   installed format's behavior. Keep each generated format skill limited to the steps it chose.

Other local skills and editors can provide useful methods for captions, color, multicam, sound
and story. Treat them as optional references: their MCP commands and applications may not be
available here, and their private assets do not become AIEditing dependencies. Adapt the method
to this runtime and prove the resulting file. If a viable route fails, report the concrete
source, platform, installation or quality blocker rather than treating a missing catalog row
as a categorical refusal.

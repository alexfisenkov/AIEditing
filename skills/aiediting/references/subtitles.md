# Subtitle timing, conversion and burn-in

Read when the request concerns SRT, WebVTT, ASS, caption appearance or subtitles in a
finished video. AIEditing has a native SRT flow in some format skills; these recipes are for
a standalone file or a one-off edit. They do not transcribe speech or reconstruct word-level
timing from sentence cues.

## Choose the deliverable

| Deliverable | Route | What changes |
|---|---|---|
| Editable text cues | Keep `.srt`, `.vtt` or `.ass`; `subtitle-convert` may shift or correct a wrongly assumed FPS | Text and cue times change; no video is rendered. |
| Styled, switchable captions | Keep `.ass` beside the video | ASS styles and font files must travel with the deliverable; players can render differently. |
| Captions visible in every ordinary player | `subtitle-burn` creates a new `.mp4` | Video is re-encoded; captions can no longer be switched off. Audio is retained. |
| Animated words, karaoke, tracked text | Use a chosen Remotion/format method | Sentence-level SRT timing is insufficient; obtain verified word times and inspect frames. |

The maintained local set uses **pysubs2 1.9.1**. `SSAFile.load`, `shift`,
`transform_framerate` and `save(format_=...)` are the relevant APIs. Read the
[pysubs2 API reference](https://pysubs2.readthedocs.io/en/latest/api-reference.html)
and [CLI examples](https://github.com/tkarabela/pysubs2/blob/master/docs/cli.rst).

```bash
python3 "<skillDir>/tools/recipes.py" subtitle-convert captions.srt captions.vtt --shift-ms 250
python3 "<skillDir>/tools/recipes.py" subtitle-convert captions.ass captions.srt --from-fps 25 --to-fps 23.976
python3 "<skillDir>/tools/recipes.py" subtitle-burn video.mp4 captions.srt captioned.mp4 \
  --font-file "/absolute/path/Onest.ttf" --font-family Onest
```

`--shift-ms` moves every cue by a constant amount. `--from-fps/--to-fps` scales every
timestamp by the input/output FPS ratio; use it only to repair a frame-rate assumption.
Neither operation maps cue times across removed pauses, rearranged shots or speed ramps.
For those changes, use the edit's actual source-to-output time map, then inspect and listen
to the first, middle and last cues. The recipe refuses negative or zero-length cues instead
of silently clipping them to zero. ASS → SRT/VTT loses the full ASS design; WebVTT cue
settings and CSS are not preserved by pysubs2, including a VTT-to-VTT rewrite. The recipe
detects STYLE/REGION blocks, cue settings and specialised cue markup and refuses them by
default. Use `--allow-style-loss` only when plain cues are intended; the report then names
the features lost. This is a processing choice the agent records, not a separate approval
dialogue. For a styled round trip, retain the original WebVTT or use a renderer/editor that
actually preserves its CSS/settings. Preserve the source file and use a new output
path; `--replace` is only for a non-source output you intentionally replace.

## Make captions readable on this canvas

The local burn route converts SRT/VTT to a temporary ASS file, copies an optional `.ttf` or
`.otf` to a short `fonts/` path, then runs FFmpeg's `ass` filter from that temporary
directory. This avoids colon, backslash and space escaping inside the filter expression on
Windows and macOS. The source and font may have spaces or non-Latin characters. The
[FFmpeg `ass`/`subtitles` filters](https://ffmpeg.org/ffmpeg-filters.html#ass) require
libass; `setup --check` checks that this machine's FFmpeg build exposes `subtitles`.

For SRT/VTT, the recipe writes an ASS canvas matching the video's width and height. It
starts with one family, one weight, an outline for contrast, and a bottom margin of 12% of
frame height for landscape or 25% for portrait. These are **starting positions**, not
platform-safe guarantees. Use `--font-size` and `--bottom-safe` after viewing a frame with
short and long text. A supplied font file must come with `--font-family`; the file and
family still need a rendered-frame check, because font substitution can be silent. Read the
file's actual family, for example with Pillow's `ImageFont.truetype(path, 24).getname()`;
do not derive it from the filename alone. If no
font file is supplied, the report calls the system font unverified.

An imported ASS file retains its styles and PlayRes by default. A bundled font must match
a family actually requested by its active styles/overrides; a different family needs
`--restyle`. A bundled file is not proof that every glyph used that font: the returned
font status remains rendering-unverified until a frame is inspected. Only `--restyle` applies
the recipe's generic definitions to every ASS style; inline overrides are still retained.
Keep a deliberate title, karaoke effect or
bilingual layout in ASS and inspect it on the final target canvas. The recipe reports the
longest visible line; it does **not** impose a universal character limit. Decide line breaks
from the spoken phrase, face position, language and target player. Check that cues do not
hide a face or platform controls, remain legible on both light and dark frames, and stay on
screen long enough to read. A cue ending after the video is refused.

The useful principles from the local Palmier caption-template skill are: choose one coherent
look, adapt it to portrait or landscape, verify the actual font, and inspect a frame inside
the caption interval. Palmier's named presets, `add_captions` calls, animations and timeline
fields are **not** AIEditing commands. For a bold per-word preset, build word-timed media
through a format skill rather than pretending ASS sentence cues carry that timing.

## Acceptance check

1. Compare cue words and time against the recording at the start, a middle change of pace
   and the last phrase. Verify names and numbers against the source, not against ASR alone.
2. Open a frame containing the longest line and a frame over a light background. Confirm
   font, outline, safe area and that the last line is not clipped.
3. Play the new video with sound. Check duration, audio stream and lip sync. Keep the
   editable subtitle file beside a burned master when the person needs later corrections.

The recipe tests cover SRT → VTT retiming, negative-time refusal and a real burn with a
font file from a path containing spaces. They do not establish typography quality on a
specific person's footage or across every subtitle player.

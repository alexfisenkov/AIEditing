# Color, shot matching and stabilization

Read for a request to fix exposure or white balance, match cameras, apply a `.cube` LUT,
steady camera motion or crop unstable edges. Choose a representative shot first and inspect
it on a calibrated or at least consistent display. The recipes here use FFmpeg 9.0.2 full;
they do not expose Palmier Pro's `inspect_color` or `apply_color` API.

## Color in the order that keeps corrections interpretable

1. **Inspect.** Record the input's pixel format, range, primaries, transfer and matrix with
   `ffprobe`. View representative frames and use luma waveform / vectorscope; use
   `signalstats` for numerical Y/U/V ranges. Metadata is a claim about the signal, not a
   measurement of its appearance. Compare the same display transform for every shot.
2. **Normalize.** Correct technical colour-space interpretation if known. Adjust exposure
   and white balance on the actual pixel data, checking highlight and shadow clipping.
   Do not bake a creative LUT over an unresolved cast.
3. **Balance and match.** Set black/white points, contrast and saturation; match shots to
   one approved reference under comparable lighting. Match skin and neutral objects as
   well as scopes. Different camera log profiles must first reach the same working space.
4. **Look.** Apply a creative curve, split tone or `.cube` LUT only after normalization.
   Confirm the LUT's expected input gamut/transfer and output space. A LUT with unknown
   provenance or colour-space assumptions is a test candidate, not an automatic fix.
5. **Verify.** Compare before/after scopes, stills and moving footage. Inspect skin,
   gradients, clipping, banding and transitions between adjacent shots.

The Palmier color-grading skill supplies this **sequence and inspection discipline**.
Its numeric `temperature`, `tint`, wheels and `lut.strength` controls are application-specific;
do not paste them into FFmpeg. FFmpeg's
[`eq`](https://ffmpeg.org/ffmpeg-filters.html#eq),
[`colorbalance`](https://ffmpeg.org/ffmpeg-filters.html#colorbalance),
[`zscale`](https://ffmpeg.org/ffmpeg-filters.html#zscale-1),
[`lut3d`](https://ffmpeg.org/ffmpeg-filters.html#lut3d),
[`signalstats`](https://ffmpeg.org/ffmpeg-filters.html#signalstats-1),
[`waveform`](https://ffmpeg.org/ffmpeg-filters.html#waveform) and
[`vectorscope`](https://ffmpeg.org/ffmpeg-filters.html#vectorscope) are distinct tools.
Check `ae.py capabilities --json` before relying on a filter.

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=pix_fmt,color_range,color_space,color_transfer,color_primaries \
  -of json input.mp4
ffmpeg -i input.mp4 -vf "signalstats,metadata=mode=print" -an -f null -
```

Changing `-color_primaries`, `-color_trc`, `-colorspace` or `-color_range` on an output
sets or overrides **metadata**. It is not by itself a pixel transform. A known transfer/
gamut conversion must be done with the proper filter and then labelled correctly. `lut3d`
changes pixels, but does not discover the source space; a mismatched LUT can create a
technically labelled yet visibly wrong file. Work on a short sample, preserve source and
record the input/output colour assumptions with any applied LUT.

## A small SDR correction and a second-shot match

The following is a **probe**, not a default grade. It assumes an already interpreted SDR
Rec.709 working image; it is not a log/HDR normalization recipe. Use a 3–5 s sample containing
a neutral object, skin if present, and the brightest important detail. Pick one approved shot
as the reference. If the second shot is slightly dark and warm, test a small display-referred
lift, contrast change and red/blue midtone balance:

```bash
ffmpeg -hide_banner -nostdin -ss 12 -i "reference-A.mp4" -t 4 -map 0:v:0 -map "0:a?" -c:v libx264 -crf 18 -c:a aac "reference-probe.mp4"
ffmpeg -hide_banner -nostdin -ss 8 -i "camera-B.mp4" -t 4 -map 0:v:0 -map "0:a?" -vf "eq=brightness=0.015:contrast=1.03:gamma=1.02:saturation=0.98,colorbalance=rm=-0.01:bm=0.015:pl=1" -c:v libx264 -crf 18 -c:a aac "B-balanced-probe.mp4"
```

Use the executable paths from `capabilities`; keep all three outputs new and in the issue
folder. The example numbers are deliberately small trial settings, not inferred measurements
of a person's footage. Compare A, the original B and corrected B with the same display
transform. Check a neutral object's cast, skin, luma waveform endpoints and vectorscope
saturation. If B's blacks rise or highlights flatten, reduce/reverse the brightness/contrast
change; change one control at a time and repeat the same excerpt. `eq` is a display-referred
adjustment, not a physical linear-light exposure control. A differently lit shot need not
match every scope trace. Approve a coherent pair, then process that continuous shot with
its recorded settings; recheck its beginning/end and the cut back to A.

For a known `.cube` LUT, first establish the **documented** input and output gamut/transfer.
For example, a creative Rec.709-to-Rec.709 LUT goes after this basic SDR balance. Put a copy
of the authorized LUT in a fresh working folder under the safe basename `look.cube`; this
keeps Windows drive colons and spaces out of the filter expression. In Python, using absolute
media paths and the selected FFmpeg executable:

```python
import subprocess
args = [ffmpeg_executable, "-hide_banner", "-nostdin", "-i", str(balanced_probe),
        "-map", "0:v:0", "-map", "0:a?", "-vf", "lut3d=file=look.cube:interp=tetrahedral",
        "-c:v", "libx264", "-crf", "18", "-c:a", "aac", str(new_lut_probe)]
subprocess.run(args, cwd=lut_work_folder, check=True)
```

Set `balanced_probe`, `new_lut_probe` and `lut_work_folder` to the actual issue paths;
check the new output does not already exist. Compare the LUT probe with the balanced
probe for clipped channels, crushed shadows, banded gradients and unintended skin shifts.
Do not apply a camera-log conversion LUT to already normalized Rec.709, or label a pixel
transform correct merely by setting output tags. An identity test LUT proves the command
path; it does not validate a creative LUT on unknown source material.

## Two-pass stabilization belongs to one continuous cut

[`vidstabdetect`](https://ffmpeg.org/ffmpeg-filters.html#vidstabdetect-1) records relative
motion in a transform file. [`vidstabtransform`](https://ffmpeg.org/ffmpeg-filters.html#vidstabtransform-1)
reads that file on a **second pass over the same frames**. The local recipe creates a
unique temporary transform file for each invocation and never reuses it across shots.

```bash
python3 "<skillDir>/tools/recipes.py" stabilize camera.mp4 stable.mp4 \
  --start 12.4 --duration 6.0 --smoothing 15
```

Cut the source into meaningful continuous plans first. `--start/--duration` selects one
source-time stretch; run the recipe separately for the next plan so camera movement does
not carry across a hard cut. The recipe analyzes that exact stretch, applies a static
optimal zoom (`optzoom=1`) and keeps the audio stream. A larger smoothing window steadies
motion but can make an intentional pan lag or make edges unstable. Review the first and last
second, extreme turns and borders. `optzoom` can crop image content; `crop=keep` fills
newly exposed borders from nearby frame content and may smear. If the subject approaches
an edge, prefer a shorter trim, a gentler value, or a deliberate output crop/pad decided
from the actual frame. Do not silently stretch the picture to hide the border.

The transform file is ephemeral and the source is never overwritten. Accept the output only
after checking that video, audio and expected duration survived. Stabilization changes
geometry. A lower VMAF against the unstabilized source need not mean the stabilized image
looks worse; measure only a genuinely aligned comparable sequence.

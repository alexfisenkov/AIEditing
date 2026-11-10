# Technical quality and evidence

Read before handing over a finished video or when asked to compare encodes. Separate four
questions: **does the file decode, do its streams and metadata match the target, is speech
and picture actually right, and is a same-content encode comparison meaningful?** One
green command does not answer the others.

## Minimum local acceptance pass

1. `ffprobe` the final file: codec, pixel format, display size/rotation, FPS, duration,
   video and audio streams, colour tags. Compare with the requested delivery target.
2. Decode the full file with FFmpeg to a null sink; a successful write alone does not prove
   every frame plays. Inspect warnings rather than discarding them.
3. Watch and listen to the opening, a representative middle scene, every unusual join and
   the ending. Check clipped words, lip sync, title/safe areas, font substitution, alpha
   edges, flashes and unintended silence. Metadata cannot verify these properties.
4. Compare the final bytes/size to the expected output file and record which file was
   reviewed. A temporary render, local build and uploaded file are separate evidence.

```bash
ffprobe -v error -show_entries \
  stream=codec_name,pix_fmt,width,height,avg_frame_rate,color_space,color_transfer,color_primaries \
  -show_entries format=duration,size -of json finished.mp4
ffmpeg -v warning -i finished.mp4 -map 0:v:0 -map "0:a?" -f null -
```

That multi-line block uses Bash continuation syntax. In Windows `cmd.exe`, use these
single-line argument forms instead (and the actual executable paths from `capabilities`):

```text
ffprobe -v error -show_entries stream=codec_name,pix_fmt,width,height,avg_frame_rate,color_space,color_transfer,color_primaries -show_entries format=duration,size -of json "finished.mp4"
ffmpeg -v warning -i "finished.mp4" -map 0:v:0 -map "0:a?" -f null -
```

Python `subprocess.run` argument lists avoid shell quoting differences altogether.

Targeted checks can help locate trouble: FFmpeg's
[`blackdetect`](https://ffmpeg.org/ffmpeg-filters.html#blackdetect),
[`freezedetect`](https://ffmpeg.org/ffmpeg-filters.html#freezedetect) and
[`silencedetect`](https://ffmpeg.org/ffmpeg-filters.html#silencedetect) report candidate
intervals, not editorial mistakes by themselves. A purposeful black card, held frame or
pause will trigger them. `signalstats` and waveform reveal clipping/levels; listening
still decides whether speech, music and transitions are acceptable. For loudness, use a
measured pass before applying `loudnorm`; a metadata target does not prove perceived
balance.

## VMAF: only for the same content on the same timeline

FFmpeg's [`libvmaf`](https://ffmpeg.org/ffmpeg-filters.html#libvmaf) accepts the distorted
encode first and the reference second. It compares corresponding frames. The native
recipe requires `--aligned-same-content` and refuses different displayed geometry/rotation
or FPS. Its container-duration tolerance is the larger of 40 ms and one nominal frame;
at 60 FPS, 40 ms is 2.4 frames. These are **coarse checks, not proof of frame alignment**. The
caller must establish that both files contain the same edit, timing and visual content.
Trim, offset, speed change, different shot, different crop or different colour transform
can make a score misleading. Align on a known source-time map before comparing, and
visually check corresponding first/middle/last frames. Do not compare a montage to its
uncut camera original.

```bash
python3 "<skillDir>/tools/recipes.py" quality encode.mp4 reference.mp4 --aligned-same-content
```

The recipe writes the FFmpeg JSON log in a temporary directory and returns its pooled
mean. It does not publish that temporary log. The numeric score is evidence for a
specific paired encode, not a universal quality grade, an audio measure or proof that the
edit fulfils the person's creative request. An identical low-resolution test file can
score below 100 with a model; do not impose a universal cutoff. Record the pair, model,
scale, alignment assumption and visual findings in the handoff. Keep the recipe's returned
JSON with the report if the result needs to be auditable later.

## What these recipes prove

The synthetic tests prove that a font-path burn retains audio, two-pass stabilization
preserves source and a selected duration, subtitle timing shifts precisely, and an aligned
pair produces a parseable VMAF score. They do not prove a real customer's captions are
readable, footage is visually stable, skin is correctly graded or a delivered platform
plays the file. State each unobserved part separately.

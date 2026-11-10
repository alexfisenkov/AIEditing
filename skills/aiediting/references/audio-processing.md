# Audio processing: choose a treatment and verify the result

These are recipes for a **copy** of a recording. Listen to the source first and measure the relevant passages. `audio-report` examines only a selected window; final loudness needs EBU R128/`loudnorm` across the entire finished audio. Identify the actual problem before adding a filter: room noise, uneven level, music masking speech, or tempo. Keep the source intact and do not apply every treatment by default.

AIEditing 0.3.0 uses its selected FFmpeg FULL executable. Find its path with `python3 "<skillDir>/tools/ae.py" capabilities --json` (`executables.ffmpeg`), then check `ffmpeg_filters` in the same JSON or run that executable with `-hide_banner -h filter=<name>`. The current selected build exposes `afftdn`, `anlmdn`, `loudnorm`, `sidechaincompress`, `atempo`, and `rubberband`; an unrelated `ffmpeg` on PATH may have fewer filters. In the examples below, replace the leading `ffmpeg` with the **quoted `executables.ffmpeg` path** if PATH resolves a different binary. The examples write **new files**. Within an AIEditing format, follow its release path and avoid normalizing audio a second time.

## Moderate stationary noise

Check a short stretch containing both speech and a pause, then try FFT denoising. `nr` is the reduction in dB; `nf` is the estimated noise floor. Start gently, around `nr=8–12`:

```bash
ffmpeg -hide_banner -nostdin -i "source.mp4" -map "0:v?" -map 0:a:0 \
  -c:v copy -af "afftdn=nr=10:nf=-50" -c:a aac -b:a 192k "denoise-check.mp4"
```

Listen to **sibilants, word tails, breaths, and pauses**. Excessive reduction can sound metallic. If the noise comes and goes, choose a different section or reduce `nr`. `anlmdn` is another built-in broadband denoiser; compare a 10–20 second A/B segment before choosing. Noise embedded in speech or music may not separate cleanly. [FFmpeg `afftdn`](https://ffmpeg.org/ffmpeg-filters.html#afftdn), [`anlmdn`](https://ffmpeg.org/ffmpeg-filters.html#anlmdn).

## Loudness and true peak

`audio-report` yields short-window dBFS, **not LUFS**. For a deliverable, use EBU R128 `loudnorm` on the entire finished audio. One pass is useful for a trial:

```bash
ffmpeg -hide_banner -nostdin -i "source.mp4" -map "0:v?" -map 0:a:0 \
  -c:v copy -af "loudnorm=I=-16:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 192k "level-check.mp4"
```

Those are example speech targets, not a universal platform requirement. For more predictable final output, make a first pass with `print_format=json` to `-f null -`. Read `input_i`, `input_tp`, `input_lra`, `input_thresh`, and `target_offset`; feed them into a second pass as `measured_I`, `measured_TP`, `measured_LRA`, `measured_thresh`, and `offset`, with the same `I/TP/LRA` targets. Linear mode can fall back to dynamic mode if the requested target conflicts with measured loudness or true peak. Measure the **rendered output** and listen to quiet and loud sections. [FFmpeg `loudnorm`](https://ffmpeg.org/ffmpeg-filters.html#loudnorm), [`ebur128`](https://ffmpeg.org/ffmpeg-filters.html#ebur128).

## Music under speech: ducking

Set the ordinary music bed low first. `sidechaincompress` reduces it while speech is present; `attack` and `release` are milliseconds. For voice and music of **matching duration**:

```bash
ffmpeg -hide_banner -nostdin -i "voice.wav" -i "music.wav" \
  -filter_complex "[1:a]volume=-20dB[m];[m][0:a]sidechaincompress=threshold=0.08:ratio=8:attack=20:release=250[d];[0:a][d]amix=inputs=2:duration=first:normalize=0[a]" \
  -map "[a]" -c:a pcm_s16le "mix-check.wav"
```

If the music is shorter, prepare and review its loop or ending first. Listen for pumping on consonants, masked opening words, and an abrupt music return after speech. Measure final loudness **after** the mix. A file being available locally does not establish rights to use it in a published video. [FFmpeg `sidechaincompress`](https://ffmpeg.org/ffmpeg-filters.html#sidechaincompress), [`amix`](https://ffmpeg.org/ffmpeg-filters.html#amix).

## Tempo without changing voice pitch

For a modest change, FFmpeg's `atempo` adjusts audio tempo without directly changing pitch. When speeding up the **whole video**, its picture must use the same factor (`setpts=PTS/1.05`), and captions, chapter markers, and scene times must be remapped. Do not apply speed twice if the format pipeline already owns it.

```bash
ffmpeg -hide_banner -nostdin -i "source.mp4" \
  -filter_complex "[0:v]setpts=PTS/1.05[v];[0:a]atempo=1.05[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 18 -c:a aac "tempo-check.mp4"
```

The selected FFmpeg FULL build also has `rubberband`, which offers separate time-stretch and pitch controls. For the same modest video acceleration:

```bash
ffmpeg -hide_banner -nostdin -i "source.mp4" \
  -filter_complex "[0:v]setpts=PTS/1.05[v];[0:a]rubberband=tempo=1.05:pitch=1[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 18 -c:a aac "rubberband-check.mp4"
```

This filter requires FFmpeg compiled with `--enable-librubberband`; check `capabilities --json` on the user's machine before offering it. For tempo above 2, FFmpeg warns that `atempo` can skip samples; chain several moderate stages instead. After either method, inspect duration, lip sync, edit joins, and the last complete word. [FFmpeg `atempo`](https://ffmpeg.org/ffmpeg-filters.html#atempo), [`rubberband`](https://ffmpeg.org/ffmpeg-filters.html#rubberband).

## Transfer from the supplied editing skills

In `multi-cam-editing`, the editor chooses master audio and checks claps, speech, and mic-to-person mapping before trimming and switching angles. In `ugc-editing`, bad takes and pauses are removed **before** captions so text stays on the right words. These principles apply here; Palmier commands do not. AIEditing works with local files through FFmpeg and its own pipeline.

## Sources

- [FFmpeg Filters: `afftdn`, `anlmdn`, `loudnorm`, `ebur128`, `sidechaincompress`, `amix`, `atempo`, `rubberband`](https://ffmpeg.org/ffmpeg-filters.html) — filter parameters and build requirements.
- `python3 "<skillDir>/tools/ae.py" capabilities --json`, `executables.ffmpeg` and `ffmpeg_filters` — the runtime-selected build, locally read back on 2026-11-10.
- `~/.codex/skills/palmier-multi-cam-editing/SKILL.md`, “Core principle”, “Step 1”, “Step 3”; `~/.codex/skills/palmier-ugc-editing/SKILL.md`, “Step 0”, “Step 2” — media inventory, sync checks, and edit order only.

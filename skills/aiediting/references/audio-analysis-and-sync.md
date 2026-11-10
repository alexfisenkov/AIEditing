# Audio analysis and synchronization across sources

Use this method for two cameras, a separate recorder, several microphones, or music that may reveal an edit point. First inventory the files: which camera shows whom, which recording is the master audio, which tracks are scratch audio, and each source's duration and frame rate. Do not switch cameras or trim files from a single offset estimate.

## What the recipes measure

```bash
python3 "<skillDir>/tools/recipes.py" audio-report "camera-A.mp4" --at 60 --window 30 --output "audio-A.json"
python3 "<skillDir>/tools/recipes.py" audio-sync "master.wav" "camera-A.mp4" --at 10 --window 5 --max-lag 2 --output "sync-A.json"
```

`audio-report` decodes **only the requested time window** to mono 8 kHz PCM. It returns peak and RMS in dBFS, their difference (`crest_db`), the fraction of short windows below −40 dBFS, and detected transient times. It is **not LUFS**, speech recognition, or a clean/dirty verdict. `librosa.feature.rms` measures short-window energy; `onset_detect` marks attacks that could be a clap, consonant, instrument, or other sound. [librosa RMS](https://librosa.org/doc/main/api/generated/librosa.feature.rms.html), [onset detection](https://librosa.org/doc/1.0.0/auto_tutorials/01-intro/05-onsets.html).

`audio-sync` compares two bounded windows. It seeks a normalized waveform match, then repeats near the end when the recordings are long enough. `--at` is a second in the **reference file** and must be at least `--max-lag`; `--window` is 1–30 seconds; search is limited to ±`--max-lag` (at most 10 seconds). The whole hour-long recording is never loaded into memory. The result includes correlation scores and the offset:

- `lag_seconds > 0`: the same event occurs **later** in target than in reference.
- `target_shift_seconds = -lag_seconds`: the suggested target timeline movement, **after verification**.
- `drift_seconds`: change in the estimate between early and late windows. More than 50 ms is rejected. For short overlap, status is `single_window`; late sync has not been checked.

Example: `lag_seconds: +0.420` means the target camera audio follows the master by 0.420 s. It does **not** mean to speed up the camera. The recipe neither shifts nor stretches a source. If the devices' clocks differ, make a separate speed-correction plan based on several reference events and check lip sync at the beginning, middle, and end.

## Accept or reject the result

1. Choose a distinctive shared event in an overlapping stretch: clap, clear phrase, or click. Avoid long silence, a metronome, or a repeating music bar; these can have several equally plausible alignments.
2. If the recipe reports silence, weak correlation, or ambiguous peaks, move `--at` to another phrase. Do not infer an offset from file names or creation timestamps.
3. After a confident estimate, **look and listen** at 2–3 short matching moments: clap or lip movement near the start, middle, and end. Check that each microphone belongs to the labeled person.
4. If the late window differs, do not force a single constant offset. Inspect sample rates, variable frame rate video, and clock drift. Even a smaller continuous clock-rate mismatch can weaken raw-waveform correlation before the 50 ms comparison runs; try shorter, distinctive windows and report the uncertainty. Correct with an explicit plan and repeat the physical check.
5. Only then plan the edit: speaker cameras usually follow the person speaking, while an A/B pair covering one subject uses B-cam sparingly to cover a join or emphasize a moment. Do not automatically cut crosstalk or laughter.

These rules adapt the local `multi-cam-editing` method's media inventory, master audio selection, mic-to-person mapping, and physical sync verification. AIEditing has no `manage_multicam` or `change_cam` operations. The `ugc-editing` method contributes the sequence “inspect A-roll and words before B-roll and captions”; it cannot substitute for verifying two recording clocks.

## Expert file access

AIEditing uses FFmpeg to decode bounded windows, NumPy/SciPy to match signals, and librosa to measure RMS and attacks. SoundFile 0.14 is useful when the input is already WAV/FLAC and should be read **in blocks**, not loaded whole:

```python
import soundfile as sf

with sf.SoundFile("master.wav") as audio:
    print(audio.samplerate, audio.channels, audio.frames)
    for block in audio.blocks(blocksize=audio.samplerate * 5, dtype="float32"):
        print(block.shape)  # five seconds at a time; replace with a local measurement
```

`sf.read(..., start=..., frames=..., dtype="float32")` reads a selected WAV window. For video and mixed codecs, use FFmpeg; SoundFile is not a video decoder. [SoundFile `blocks` and `read`](https://python-soundfile.readthedocs.io/en/latest/index.html). The analysis copy's 8 kHz sample rate does not change any source or final deliverable.

## Sources

- [librosa 1.0, `feature.rms`](https://librosa.org/doc/main/api/generated/librosa.feature.rms.html) — short-window RMS.
- [librosa 1.0, onset detection tutorial, Output units](https://librosa.org/doc/1.0.0/auto_tutorials/01-intro/05-onsets.html#output-units) — transient time units and conversion.
- [SoundFile, `read` and `blocks`](https://python-soundfile.readthedocs.io/en/latest/index.html) — bounded reading and block iteration; the installed SoundFile 0.14.0 API was also inspected locally.
- `~/.codex/skills/palmier-multi-cam-editing/SKILL.md`, “Core principle” and “Step 1–3”; `~/.codex/skills/palmier-ugc-editing/SKILL.md`, “Step 0–2” — master audio, physical sync check, and edit order.

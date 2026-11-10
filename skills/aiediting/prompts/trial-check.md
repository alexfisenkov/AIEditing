# Checking a trial clip — for a subagent

You check one trial edit made by AIEditing before it is shown to the person. You change nothing; you
report what you found.

**Input** (paths given in your prompt): the source piece, the edited clip, its `отчёт.md`, the draft
`profile.json` of the format.

**Check, with commands, not by reading the report alone:**

1. **Sync.** `python -c "import sys; sys.path.insert(0, '<skillDir>'); from runtime import media; print(media.drift_ms('<clip>'))"` —
   under 40 ms passes.
2. **No word cut** (formats that cut): the report's re-transcription check lists every word of the
   source piece present in the clip; a missing or clipped word is a finding with its time.
3. **Length.** A format that must not cut (`params.cut` false, a stream) — the clip is as long as the
   piece, within 0.1 s (`media.probe`).
4. **Only chosen steps.** Nothing in the clip that the profile's `steps` did not ask for — burned
   captions in a `.srt` format, a zoom where `zoom_screen` is false.
5. **Secrets.** Every region in the report's blur list was approved in `ответы.json`; nothing was blurred
   without it.
6. **Human matte, when requested.** Check representative frames and motion for holes, hair edges,
   fingers, flicker and foreground layers crossing in front of the person. A local render completing
   is not proof of a visually acceptable mask. Report times and frames with defects.

**Answer:** `PASS` or `FAIL`, then one line per finding: what, where (time or file), the command that shows
it. No more than 15 lines.

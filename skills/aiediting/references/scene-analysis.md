# Scene analysis: boundaries, not take selection

Use this method when a recording already contains cuts, camera changes, or inserted footage and you need **source-file time boundaries**. It does not decide which take is best, who is speaking, where a semantic chapter begins, or whether a passage should be removed. Check the proposed boundaries against frames and short clips with sound before editing.

## Choose the detector

AIEditing pins PySceneDetect 0.7.3. `ContentDetector` compares adjacent frames; a lower threshold finds more changes. `AdaptiveDetector` compares a change to its surrounding window and can reduce false cuts caused by camera motion. Both target fast cuts. PySceneDetect also has `ThresholdDetector` for fades to/from black, but AIEditing's `scenes` recipe does not wrap that detector yet. See the [official examples](https://www.scenedetect.com/docs/latest/examples.html) and [detector parameters](https://www.scenedetect.com/docs/latest/api/detectors.html).

Start with a bounded part of the original video:

```bash
python3 "<skillDir>/tools/recipes.py" scenes "source.mp4" --start 30 --end 90 --detector content --min-scene 0.6 --output "scenes.json"
```

`--start` and `--end` are seconds in the **original file**. The JSON has `scenes[].start_seconds/end_seconds`, frame numbers, and `cuts_seconds`. If no cut is detected, it contains one interval and no cuts. `--output` refuses to overwrite an existing file unless `--replace` is passed. This recipe does not cut or alter the source.

Try `--threshold 20` when obvious hard cuts are missed; raise it toward 35 when movement or flashes produce extra cuts. The default content threshold of 27 is a starting point, not a universal setting. For a moving camera, try `--detector adaptive`; its default threshold is 3. Do not compare those two threshold scales directly.

**`--min-scene` uses seconds.** PySceneDetect's Python API defaults to 15 **frames**, while its own CLI defaults to 0.6 **seconds**. For a rapid montage, try 0.2–0.4 seconds. A large minimum suppresses real short shots. See [Set a Minimum Scene Length](https://www.scenedetect.com/docs/latest/examples.html#set-a-minimum-scene-length).

## Accept or reject the result

1. Open a frame on each side of 3–5 reported boundaries and listen across them. For a boundary at 60 seconds, inspect around 59.8 and 60.2 seconds, for example with `ffmpeg -ss 59.8 -i "source.mp4" -frames:v 1 "before.png"` on a disposable copy or in a temporary work folder.
2. Check the first and last intervals against the source duration. State when only part of the file was analyzed.
3. If the edit follows words, read the transcript separately. A camera change may occur mid-sentence; a frame boundary is no permission to cut audio.
4. With variable frame rate footage, compare **seconds** against a player. The reported `fps` is an average value; frame numbers may not map reliably into an external timeline.

**Failure signs:** many cuts during pans → adaptive detector or higher threshold; missed short shot → lower `--min-scene`; missed gradual fade → use PySceneDetect's fade detector separately. Duplicate frames and heavy compression may need manual review. The recipe does not enable `frame_skip`, which can miss short shots. [SceneManager `frame_skip`](https://www.scenedetect.com/docs/latest/api/scene_manager.html).

## Transfer from the supplied editing skills

The local `multi-cam-editing` method inventories angles and audio, verifies sync, then plans cuts around speakers and sentences. `ugc-editing` inspects speech and retakes before adding B-roll. AIEditing adopts that **review order**, not Palmier commands: `manage_multicam`, `change_cam`, and `inspect_timeline` are not AIEditing APIs. Scene boundaries are evidence for a later editorial decision.

## Sources

- [PySceneDetect 0.7.3, Examples: Pick a Detector, Set a Minimum Scene Length, Analyze Only Part of the Video](https://www.scenedetect.com/docs/latest/examples.html) — detector choice, thresholds, interval, and time units.
- [PySceneDetect 0.7.3, Detectors: ContentDetector and AdaptiveDetector](https://www.scenedetect.com/docs/latest/api/detectors.html) — threshold semantics and camera-motion behavior.
- [PySceneDetect 0.7.3, SceneManager: detect_scenes and get_scene_list](https://www.scenedetect.com/docs/latest/api/scene_manager.html) — source timecodes and `frame_skip` limits.
- `~/.codex/skills/palmier-multi-cam-editing/SKILL.md`, “Core principle” and “Step 1–3”; `~/.codex/skills/palmier-ugc-editing/SKILL.md`, “Step 0–2” — editorial sequence only; no Palmier API is carried into AIEditing.

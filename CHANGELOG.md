# What's new in AIEditing

## Unreleased

- A format skill says to use `python3` where there is no `python`, as the workshop already does.
- A format «Нарезка»: from a finished horizontal video, 9:16 clips with the picture whole in the centre, a headline and a call to action on the fields (`bands`), and a short teaser with a Play button, fast-forwards and a bar of the whole video's time (`teaser`). The model picks the clips by `method/clips.md`.
- A format can have paths: `variants` in `catalog/formats.json`, one row and a preset each. The workshop offers them, makes a short probe of each on the person's video (`ae.py trial --variant`), shows them side by side and builds only after a choice (`ae.py variant`); `build-skill` refuses without one. Without questions it chooses itself and says so.
- «Нарезка» has a second path, `reedit`: a re-edit for 9:16 by the overlay kit, with the preset `repurpose-reedit`, the step `reedit` and `method/reedit.md`. The pipeline agrees the clips and hands over `отрывки.json` and the words; the model makes the clips. A built skill has run on a real video as far as the clips, and the kit has made a real clip; a whole new video through a built skill has not been made yet.
- Overlay kit: `vertical.md` and the commands `vertical-init`, `vertical-check`, `vertical-words`, `vertical-final`, `vertical-sheets`. Every frame is audited for what overlaps, sits edge to edge, leaves the screen empty or leaves the safe zone. The sound comes only from clean speech (`prepare --speech`), a finished clip is measured for a hum, and the call to action stands long enough to read.
- Refining is open to any `монтаж-*`: a skill with no profile is opened as a copy and put back in place; files a profile does not describe stay (`own/`, `design/method.md`), and a `SKILL.md` edited after its build is named. `ae.py show` puts a clip the model made on the dashboard.
- A kit copied into a format now lists the hash of each file: a kit changed after its build stops the build instead of being wiped, and `ae.py kit <skill> own|renew` is the person's choice. `run.py hear` and `ae.py hear` print what the recogniser hears in a finished clip.
- `ae.py formats "<word>" --like <format>`: a narrow skill under the person's own word has the start and the paths of a format from the list. `ae.py trial --variant own:<word>` probes a way the catalog lacks beside the others.
- Two clips whose file names differ only in case or in composed letters are refused: the second would have replaced the first without a word.
- «Выпуск YouTube» no longer promises part-by-part approval, which is not built: its preset is `plan`.
- A format skill no longer claims a bare «смонтируй <путь>» when several `монтаж-*` skills are installed: the agent asks which format first.
- A 9:16 clip: `drop` takes sentences out of it, `name` names its file, `params.layout.background` colours the fields; `max_seconds` now counts the finished clip, after `speed`. The clip rubric marks down a clip that points at what a short does not have («под этим видео»).

## 0.1.0 — 2026-11-04

The first public version.

- «Без вопросов»: one message and a recording give the finished video and the installed skill; `phases/no-questions.md`, `ae.py init --no-questions`, `approval: auto`, `run.py edit --no-questions`. Confirmations are accepted, judgements are the agent's, a found secret is closed, every decision goes into the report.
- The `graphics` step: scenes written by the model on top of the finished video, with or without cuts; `overlay-kit/`, the `overlay` preset and a format «Наложения», `ae.py formats --preset`.
- A format skill's `SKILL.md` carries only the method it needs: `templates/format-skill/method/`.
- Overlay kit: the camera follows the face without steps (median, Gaussian, spline instead of the nearest point of the track); `time-map.json` lets a finished video take cuts by markers while scenes keep their seconds; the README holds the lessons of a 73-marker review.
- A format «YouTube с графикой»: clean speech from takes (`tools/takes.py`, a word's edge follows the sound), graphics on top, edits by markers (`tools/markers.py`, `tools/recut.py`, `takes-and-markers.md`). `phases/refine.md` says where a remark goes.
- Foundation: repository layout, one test command, CI on macOS and Windows, a monthly install check.
- Speech recognition with four providers and one word format: local whisper.cpp, ElevenLabs Scribe, any OpenAI-compatible endpoint (OpenRouter included), or your own command. Keys are read by variable name: from the environment, a `.env` file or `asr.key_file`.
- Editing mechanics on ffmpeg: file passport, speech detection, pause removal with a margin around speech in one pass, A/V drift check, loudness normalisation, `.srt` with a brand glossary.
- Format profile schema and a dependency-free profile check.

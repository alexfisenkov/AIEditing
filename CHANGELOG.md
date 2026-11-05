# What's new in AIEditing

## Unreleased

- `params.speed` goes on once, in `run.py edit`. The clean speech stays at the speed of the recording, so its `speed` no longer doubles (1.145 instead of 1.07), and a recogniser hears normal speech: a whole video by its first hearing, a cut one by a second hearing before the speed-up, `verify_words` too. The report says the length, and a length that does not fit is named. `recut.py plan` moves a `pieces.json` of another rate to the rate of the finished video.
- A whole recording is a way: `takes.py trim` keeps everything between the first and the last word, and `takes.py init` makes the config from the file. `params.recording`: `takes`, `trim` or `whole`. A clean speech built from a source that is not 30 fps no longer runs at the wrong speed.
- Corrections of subtitles work on words, not on subtitle text, so they do not depend on where a subtitle breaks. `replace` is exact, `at` is one place near a second, an empty `to` takes words out, and what found no words is named. The `.srt` and `слова-таймкоды.txt` come from one list, and `run.py subtitles` puts corrections on both with no render. `run.py hear --from --to` hears a narrow piece.
- A glossary with a phrase and its first word («клод код», «клод») no longer makes «Claude код», and quotes around a word stay.
- New versions. On a real video through `final` and `sync`: ffmpeg 9.0.2 (`-filter_script` is gone, `recut.py` uses `-/filter`; loudnorm flushes a tenth of a second more, `final` holds the sound to the picture), whisper.cpp 1.9.5, Remotion 4.0.541 (licence text unchanged), React 19.3.1, TypeScript 7.0.2. By a smaller check: Playwright 1.64.1 (one captured page), HyperFrames 0.9.16 (its real render test), tesseract 5.5.4 (one picture). Node from 22.12, which Remotion's bundler needs. OpenCV stays on 4.14: version 5 gives nothing here and changes what we use. The licence line now says what it says: individuals, companies of up to three employees, non-profits.
- The file with graphics comes out in H.264 yuv420p, limited range, BT.709 with all three tags, and `final` refuses anything else. Before this it had full range or no tags, by Remotion's version, and a delivery pipeline refused it.
- A second round of markers has a way: the map always leads from the first accepted video, `recut.py old` takes a second back to it, `prepare --keep-face` keeps the face track in the scenes' seconds. `recut.py build` no longer writes through a finished video linked to it.
- The interview starts with the recording: cut or whole, speed, where the text comes from, in that order. `catalog/params.json` names who applies each parameter, `tools/aelib/coherence.py` refuses a format whose answers do not fit together, and `phases/refine.md` has «One parameter, one place».
- Brief of the scene executor: the stage is filled by the time a layout change ends, a graphic takes most of it and stands in its middle, a condition in the speech stays on screen. The sample scenes now show this too.

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

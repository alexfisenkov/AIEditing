# Clean speech: takes or a trimmed recording, and edits by markers

For a video that goes on from the speaker's recording, not from the file as it is: a long video for a channel. Only a 16:9 frame: `recut.py` builds 1920x1080, and `takes.py init` refuses any other shape. A format where the file stays untouched, `params.recording` `whole`, does not use this file.

`<kit>` is this folder. `<dir>` is the clean speech's folder, and the method of the format names it. `tools/takes.py`, `tools/recut.py` and `tools/markers.py` run in the AIEditing environment (`~/.aiediting/venv/bin/python`); their first lines give the config. Long commands go in the background.

## One speed, one hearing

`speed` in the config is `params.speed` of the format: the rate of the finished video. Here it only says in whose seconds `pieces.json`, the cuts and the mutes are, so that a marker from the finished video lands where it was put. Nothing here plays faster: `clean-speech.mov` stays at the speed of the recording. `run.py edit` applies the speed, once, and the recogniser hears the speech before it, because it hears sped-up speech worse and makes up repeats. The finished video lasts `clean-speech.mov` ÷ `speed`.

Choosing takes always hears by local whisper, whatever recogniser writes the `.srt`, because it needs a word's time in the recording.

## Which way

| The person says | Way | Command |
|---|---|---|
| «лучшие дубли», «вырежи повторы и паузы», or nothing, and the format's `params.recording` is `takes` | Takes | `takes.py plan` |
| «только края», «цельная запись», «не резать», or nothing, and it is `trim` | Trim | `takes.py trim` |
| «как есть», not even the edges | none | the file itself goes to `run.py edit`; this file is not for it |

Both ways start the same:

1. `takes.py init "<recording>" "<dir>/config.json" --out "<dir>" --speed <params.speed> --model "<asr.model of the profile>" --language <language of the profile> [--prompt "<names the recogniser mishears>"]`: its sound as mono 48 kHz, spans for the recogniser, the config. With another recogniser in the profile, `--model` is `params.verify_asr.model` or a file in `~/.aiediting/models/`. Several recordings: add each to `recordings` and `segments` by hand.
2. `takes.py words "<dir>/config.json"`, then read `words-lines.txt` in full. Recognise in pieces: a long file makes the recogniser loop.

## Takes

3. Choose the best take of each thought, in the order of the video, into `takes` and `exclude`. The script's order is not the recording's.
4. `takes.py plan <config>`. Read `speech-text.txt` as a whole: it must read as one speech. With `approval: plan` it goes to the person now, before the build; without questions the choices go into your list.
5. `recut.py build <config>`, `recut.py joins <config>`. Every join reads right, or the plan changes. This is the check of the cuts on this way: `verify_words` sees only the speech already made.
6. `<dir>/clean-speech.mov` goes to `run.py edit` as the video.

What must not stay:

- a piece under 0.6 s nobody listened to: a mumble, a cough, a look aside. In one review all eleven the person marked were exactly that;
- silence or reading from a screen: the speaker looks aside or down, and a recogniser writes a caption credit on silence;
- a technical line meant for the agent;
- the same thought said twice;
- a clipped word. `takes.py` moves a word's edge to where the sound really ends, because a recogniser's word times are off by tenths of a second. Check a piece's start too: the tail of the previous word turns into mush. A remark «the join swallowed a word» can need the start later, not earlier: try both and listen.

## Trim

Nothing inside is cut: pauses, breaths and what is said twice stay.

3. `takes.py trim <config>`: one piece per recording, from the first word to the last, with a little air. It prints what went from each end, and the first and last words.
4. Look at both edges: `ffmpeg -ss <first second> -i "<recording>" -frames:v 1 "<dir>/начало.jpg"`, and the same for the last. The speaker reaching for the keyboard before the first word, or looking aside after the last, is cut by hand: `"trim": {"A": [from, to]}` in the config, seconds of the recording, and `takes.py trim` again.
5. `recut.py build <config>`. There are no joins to check.
6. `<dir>/clean-speech.mov` goes to `run.py edit` as the video.

## Edits by markers

The person marks the finished video in an editor and exports it. Final Cut: `markers.py <export> <out.json>`; another editor: the seconds by hand. Dictated labels are free text; a cut is a pair of "from here" and "up to here", and a misheard word for "cut" is still a cut.

**In whose seconds, once the speech has changed:**

| What | Seconds of |
|---|---|
| scenes, `layouts`, `face.json`, `useT`, markers of the first round, `cuts` and `mute` in the config | the first accepted video |
| `raw/words.txt`, `overlay.py frame`, `sheets`, `.srt`, `at` in `ответы.json` | the file now in `public/clips/source.mp4` |
| `run.py hear "<dir>/clean-speech.mov"` | the same file × `speed` |

`time.ts` goes between them: `toOld(second of the file)`, `toNew(second of a scene)`, and `recut.py old <config> <second>` prints the first of these.

1. Say that everything was read, ask the open questions in one list, and do not start before the answer: a cut they may still change is expensive. Without questions, decide: in doubt the words stay, and the doubtful cuts go into your list.
2. Check every cut by ear before building: what is in it and how the join reads. A marker's second × `speed` is its place in `clean-speech.mov`.
3. Copy `<W>/src` to `<W>/raw/rollback/`, and `<W>/public/clips` to `<W>/raw/rollback/clips`. Copy `<dir>/pieces.json` to `<dir>/принято.json` once, at the first round, and `clean-speech.mov` beside it: `pieces` in the config always names this copy, because `plan` writes over `pieces.json`.
4. `recut.py plan`, `recut.py build`, `recut.py joins`, `speed` as it was. Mute in the config what must be silent without moving anything.
5. `run.py edit "<dir>/clean-speech.mov" --out "<issue folder>"`: the speed goes on, and the `.srt` and the words come anew. An `at` correction in `ответы.json` is in the seconds of the previous file: move it, or the report names it as found nowhere. Then `overlay.py prepare` on that video and those words again, with `--keep-face`: it keeps the scenes and the face track and puts the new clips and length in place. Copy `<dir>/time-map.json` into `<W>/src/data/`.
6. **Scenes do not move.** They stay in the seconds of the first accepted video: `useT` returns those seconds, so markers address scenes directly. Anything timed in frames, such as a `Sequence` for a video inside a scene, goes through `toNew(at)`. Cues inside a removed span go silent by themselves.
7. By hand on cuts of a second or more: move a layout change to the end of the cut, appearances to the first word after it, departures before it, and remove the scene that talked about what was cut. A word's second in `raw/words.txt` goes through `toOld` before it goes into a scene.
8. Write the final under a new name; do not overwrite the accepted file. Check the sound against the new video of step 5, and each marker by a frame of `toNew(its second)`.

**A second round of markers.** The map always leads from the first accepted video, and there is one map. So the new markers, in seconds of the latest file, go through `recut.py old` first, join the old `cuts` in the config, and `plan` runs again from `принято.json`.

# Clean speech from takes, and edits by markers

For a video where the speaker's raw recordings hold repeats, silence while something runs, and reading from a screen: a long video for a channel. A format where the recording stays whole does not use this file.

`<kit>` is this folder. `tools/takes.py`, `tools/recut.py` and `tools/markers.py` run in the AIEditing environment (`~/.aiediting/venv/bin/python`); their first lines give the config. Long commands go in the background.

## Clean speech

1. `takes.py words <config>`, then read `words-lines.txt` in full. Recognise in pieces: a long file makes the recogniser loop.
2. Choose the best take of each thought, in the order of the video, into `takes` and `exclude`. The script's order is not the recording's.
3. `takes.py plan <config>`. Read `speech-text.txt` as a whole: it must read as one speech.
4. `recut.py build <config>`, `recut.py joins <config>`. Every join reads right, or the plan changes.
5. `clean-speech.mov` is the video the graphics go on top of.

What must not stay:

- a piece under 0.6 s nobody listened to: a mumble, a cough, a look aside. In one review all eleven the person marked were exactly that;
- silence or reading from a screen: the speaker looks aside or down, and a recogniser writes a caption credit on silence;
- a technical line meant for the agent;
- the same thought said twice;
- a clipped word. `takes.py` moves a word's edge to where the sound really ends, because a recogniser's word times are off by tenths of a second. Check a piece's start too: the tail of the previous word turns into mush. A remark «the join swallowed a word» can need the start later, not earlier: try both and listen.

## Edits by markers

The person marks the finished video in an editor and exports it. Final Cut: `markers.py <export> <out.json>`. Dictated labels are free text; a cut is a pair of "from here" and "up to here", and a misheard word for "cut" is still a cut.

1. Say that everything was read, ask the open questions in one list, and do not start before the answer: a cut they may still change is expensive.
2. Check every cut by ear before building: what is in it and how the join reads.
3. Copy `<W>/src` to `<W>/raw/rollback/`.
4. `recut.py plan`, `recut.py build`, `recut.py joins` with the accepted `pieces.json` as `pieces`. Mute in the config what must be silent without moving anything.
5. Put the new video in place: `public/clips/source.mp4`, `public/clips/speech.wav`, `time-map.json` into `src/data/`, the new length into `DURATION`. Keep the previous clips until acceptance.
6. **Scenes do not move.** They stay in the seconds of the accepted video: `useT` returns those seconds, so markers address scenes directly. Anything timed in frames, such as a `Sequence` for a video inside a scene, goes through `toNew(at)`. Cues inside a removed span go silent by themselves.
7. By hand on cuts of a second or more: move a layout change to the end of the cut, appearances to the first word after it, departures before it, and remove the scene that talked about what was cut.
8. Write the final under a new name; do not overwrite the accepted file. Check the sound against the new clean speech, and each marker by a frame.

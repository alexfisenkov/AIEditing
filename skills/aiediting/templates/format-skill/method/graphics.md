## Graphics

`run.py edit` makes the video without graphics, `<video>.mp4` in the issue folder, and `слова-таймкоды.txt` beside it,
in seconds of that video. The graphics go on top of them: **read `<skillDir>/design/overlay-kit/README.md` and follow
it**, with `python "<skillDir>/design/overlay-kit/tools/overlay.py"` as its command, and these values:

- `prepare "<issue folder>/<video>.mp4" "<working folder>" --words "<issue folder>/слова-таймкоды.txt" --design "<skillDir>/design"`,
  plus `--logo` with `<skillDir>/design/logo.svg` or `logo.png` when it exists. A design system they named for this
  video replaces the `--design` folder, and that logo, for this run.
- The working folder: `~/.local/share/overlay-kit/<skill name>/<issue folder name>`, an absolute path.
- `final "<working folder>" "<issue folder>" "<name> - монтаж.mp4" --lufs <params.lufs of profile.json>`, then
  `sync "<issue folder>/<video>.mp4" "<issue folder>/<name> - монтаж.mp4"`. `<name>` is `<video>`; with clean speech, the name of the recording.

Another `run.py edit` into the same issue folder rewrites its report: run `prepare` and `final` again after it. The run
is not finished until the file with graphics is in the issue folder and its sound is checked against the video
it was made from. Say so if you stop earlier. `final` and `sync` end with code 1 when the speech moved or the length
changed: that is a defect to fix by the README, not a result to hand over. The `.srt` beside the video has the same
times, so it stays right. With nothing cut, `<video>.mp4` is a hard link to the source: never edit it in place.

What is said stays as said: a slip does not go on screen, and the `.srt` keeps what was heard, with mistakes of the
recogniser corrected. A correction goes into `ответы.json` under `srt`, and `python "<skillDir>/tools/run.py" subtitles "<issue folder>"`
puts it on the `.srt` and `слова-таймкоды.txt` together, in seconds, with no render; code 1 and a line mean a correction found no words,
so copy them from the `.srt`. Neither file is edited by hand: the next `run.py edit` writes over it. `prepare` copies the words into
`raw/words.txt`: after a correction run `prepare` again, it keeps the scenes. A doubtful place is heard at the speed of the recording, in a
narrow piece: `run.py hear "<the file given to run.py edit>" --from S --to E`, in seconds of that file, which are the seconds of the finished
video × `params.speed`; a recogniser hears sped-up speech worse and makes up repeats. So a word that matters on screen is checked there
before it goes into a scene. Scene times must fit the sound: a word far from its place in the file is corrected in `raw/words.txt`, for the
scenes, after the last `prepare`. A recording that ends mid-word ends so, when the person
asked to leave it as it is. The design's colour rules hold: a design with an accent and no «ok» uses the accent for that token.
Nothing here is a reason to ask.

`<skillDir>/design/sources.md`, when it exists, says where this person's materials live: read it before the scenes.

The working folder lies outside the issue folder because rendering from a cloud-synced folder hangs: it is the one place
this step writes elsewhere. The Node packages and the renderer's browser come on the first run; those downloads, the
logos and the pages the person named are the only network this step uses, besides the recogniser.


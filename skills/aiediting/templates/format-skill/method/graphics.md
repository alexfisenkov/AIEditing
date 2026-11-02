## Graphics

`run.py edit` makes the video without graphics, `<video>.mp4` in the issue folder, and `слова-таймкоды.txt` beside it,
in seconds of that video. The graphics go on top of them: **read `<skillDir>/design/overlay-kit/README.md` and follow
it**, with `python "<skillDir>/design/overlay-kit/tools/overlay.py"` as its command, and these values:

- `prepare "<issue folder>/<video>.mp4" "<working folder>" --words "<issue folder>/слова-таймкоды.txt" --design "<skillDir>/design"`,
  plus `--logo` with `<skillDir>/design/logo.svg` or `logo.png` when it exists. A design system they named for this
  video replaces the `--design` folder, and that logo, for this run.
- The working folder: `~/.local/share/overlay-kit/<skill name>/<issue folder name>`, an absolute path.
- `final "<working folder>" "<issue folder>" "<video> - монтаж.mp4" --lufs <params.lufs of profile.json>`, then
  `sync "<issue folder>/<video>.mp4" "<issue folder>/<video> - монтаж.mp4"`.

Another `run.py edit` into the same issue folder rewrites its report: run `prepare` and `final` again after it. The run
is not finished until the file with graphics is in the issue folder and its sound is checked against the video
it was made from. Say so if you stop earlier. `final` and `sync` end with code 1 when the speech moved or the length
changed: that is a defect to fix by the README, not a result to hand over. The `.srt` beside the video has the same
times, so it stays right. With nothing cut, `<video>.mp4` is a hard link to the source: never edit it in place.

What is said stays as said: a slip does not go on screen, and the `.srt` keeps what was heard, with mistakes of the
recogniser corrected. Scene times must fit the sound: when hearing the video shows `слова-таймкоды.txt` wrong, correct
the file before `prepare`. A recording that ends mid-word ends so, when the person asked to leave it as it is. The
design's colour rules hold: a design with an accent and no «ok» uses the accent for that token. Nothing here is a reason
to ask.

The working folder lies outside the issue folder because rendering from a cloud-synced folder hangs: it is the one place
this step writes elsewhere. The Node packages and the renderer's browser come on the first run; those downloads, the
logos and the pages the person named are the only network this step uses, besides the recogniser.


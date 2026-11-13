## Without questions

The profile says `approval: auto`, or the person asked for it in this request («без вопросов», «не спрашивай», «сам всё
сделай», «как я сказал, так и делай»; then add `--no-questions` to step 2). A wish for speed is not this. Nothing goes to
the person until the finished video. Exit code 3 then means **you** decide:

<!-- unless reedit -->
- `editing`, `retakes`: keep what you doubt, cut what is plainly a repeat or a slip.
- `repeats`: the same, a repeat is taken out only when it is plainly the same thought said again.
- `chapters`, `cards`, `animations`: their text comes only from what is said; leave out what does not earn its place.
<!-- end -->
- `clips`: take the highest scored; when the skill has the section «Clips from a finished video», pick by it, with `headline` and
  `teaser` where this skill has them.
<!-- if broll -->
- `broll`: the proposals stand and nothing is asked: each insert is a line of the report with who is in its frame, and the re-shoot list
  is written. A person they asked not to show is never inserted; stock only by the key they already set.
<!-- end -->
<!-- unless reedit -->
- `layout`: look at the frames it names and set `kind` and `face`.
- `secrets`: everything with a box goes under the blur by itself. A secret said aloud has no box: it stays in the sound,
  the `.srt` and the words files, so it goes first in your list, named by its kind and time, not by its value.

**After every run, whatever its exit code.** The run is silent about what it could not see, so look yourself, in frames of
the finished video:

<!-- end -->
<!-- if blur_regions -->
- A format that shows a screen: names, chat titles and the like are not found by the search. Add areas and run again:
  `{"secrets": {"ok": true, "payload": {"extra": [{"x": …, "y": …, "w": …, "h": …, "start": …, "end": …, "what": "названия
  чатов"}]}}}`. One frame from each closed stretch shows whether the blur covers it all; a tail left open is widened the
  same way.
<!-- end -->
<!-- if no_blur -->
- A screen in the video: this format has no blur. What must not be seen is kept out by the crop and the choice of scenes, and named
  first in your list when it stays in the recording.
<!-- end -->
<!-- unless reedit -->
- The `.srt`: a mistake goes into `{"srt": {"ok": true, "payload": {"replace": {"как услышано": "как надо"}, "at": [{"t": 123.4,
  "from": "как услышано", "to": "как надо"}]}}}`, then `python "<skillDir>/tools/run.py" subtitles "<issue folder>"`: no new render, and
  it names what found no words. `replace` is whole words, with the case as they stand in the `.srt`, everywhere they occur; `at` is the
  one place near that second of the finished video, and an empty `to` takes the words out. Never by hand in the `.srt`: the next run
  writes over it. Words come from the recogniser: on local whisper they can be missing or wrong around cuts, so a format that cuts on
  it says that in your list.
- `blur_track`: look at the frames. The box follows the secret → yes. It does not → no, and that secret goes first in
  your list, because it stays open.
<!-- end -->
<!-- if reedit -->

**Secrets on this path.** No search and no blur run here: the pipeline makes no picture to close anything on. You keep them out of the
frame, by the crop of each screen and the choice of scenes, by «Screens» in `vertical.md`, and you look for them in the sheets and in
the finished clip. A secret said aloud stays in the sound and in the words file: it is left out of the clips by `drop`, or it goes
first in your list, named by its kind and time, not by its value.
<!-- end -->

Write your decision into `ответы.json` as in step 3 and run again. The report lists the answers. What you cannot know or
check is not asked either: it is named in your last message, as one list, with whether secrets were looked for at all.
Publishing, generating, paying and keys stay closed, and speech goes only to the recogniser this format already uses.


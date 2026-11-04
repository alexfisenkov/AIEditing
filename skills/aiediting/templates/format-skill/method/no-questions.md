## Without questions

The profile says `approval: auto`, or the person asked for it in this request («без вопросов», «не спрашивай», «сам всё
сделай», «как я сказал, так и делай»; then add `--no-questions` to step 2). A wish for speed is not this. Nothing goes to
the person until the finished video. Exit code 3 then means **you** decide:

<!-- unless reedit -->
- `editing`, `retakes`: keep what you doubt, cut what is plainly a repeat or a slip.
- `chapters`, `cards`, `animations`: their text comes only from what is said; leave out what does not earn its place.
<!-- end -->
- `clips`: take the highest scored; when the skill has the section «Clips from a finished video», pick by it, with `headline` and
  `teaser` where this skill has them.
<!-- unless reedit -->
- `layout`: look at the frames it names and set `kind` and `face`.
- `secrets`: everything with a box goes under the blur by itself. A secret said aloud has no box: it stays in the sound,
  the `.srt` and the words files, so it goes first in your list, named by its kind and time, not by its value.

**After every run, whatever its exit code.** The run is silent about what it could not see, so look yourself, in frames of
the finished video:

- A format that shows a screen: names, chat titles and the like are not found by the search. Add areas and run again:
  `{"secrets": {"ok": true, "payload": {"extra": [{"x": …, "y": …, "w": …, "h": …, "start": …, "end": …, "what": "названия
  чатов"}]}}}`. One frame from each closed stretch shows whether the blur covers it all; a tail left open is widened the
  same way.
- The `.srt`: a mistake goes into `{"srt": {"ok": true, "payload": {"replace": {"как услышано": "как надо"}}}}`, and the run
  again. Words come from the recogniser: on local whisper they can be missing or wrong around cuts, so a format that cuts on
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


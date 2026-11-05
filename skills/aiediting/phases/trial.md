# Trial edit

`ae.py stage trial`. The only edits the workshop makes, to show, through what the format skill will run: one piece of the person's
source; or, for a format with paths, a short probe of each path and then the full trial of the chosen one. It loops until the
person says «да» — there is no limit.

## Run

```bash
python "<skillDir>/tools/ae.py" trial <skill> "<source>" --start <S> --duration <D>
```

Pick a piece of 1–2 minutes that has what the format does (pauses for a lesson, a secret on screen for
a stream, a strong phrase for a vertical); a vertical may take the whole source. Camera and screen are
two files (separate tracks) → add `--screen "<screen file>"`: it is cut to the same piece. The result is in
`.aiediting-work/<skill>/trials/NN/out/` and on the dashboard.

A format that makes several files from one source (`нарезка`) runs on the whole source, without `--start`: the clips are
picked from all of it. The dashboard shows the first file; every one is in `out/`, and all of them are what is shown.

**Exit code 3 — a decision is needed** (the plan, the cut list, the regions to blur, the clips). Read
`trials/NN/вопросы.json`, show it to the person in plain words (frames, times, the list), and write
their answer to `trials/NN/ответы.json` as `{"<key>": true}`, `{"<key>": false}` or
`{"<key>": {"ok": true, "payload": {...}}}` with what they changed. Then the same call with
`--answers trials/NN/ответы.json`. Never approve on their behalf.

A format with `params.clean_speech`: the piece must show its way, so a trial starts from the speech, not the raw recording. Make `clean-speech.mov` from
the piece by `overlay-kit/takes-and-markers.md` in `trials/NN/речь`, then `ae.py trial <skill> "<that file>"`.

A format with `graphics`: the trial is the base; put the graphics on it by `overlay-kit/README.md`, the
working folder for this piece kept until the «да». The clip shown is the one with graphics:
`ae.py show <skill> "<file>"` puts it on the dashboard in place of the base.

A format with `reedit`: the trial makes no video, it agrees the clips and prints where `отрывки.json` and
`слова-таймкоды.txt` are. Make the clips by `templates/format-skill/method/reedit.md` and `overlay-kit/vertical.md`, then
`ae.py show <skill> "<file>"`. The checks there hold for a trial too. It runs on the whole source and refuses `--start` and
`--duration`: the seconds of its clips, words and clean speech are those of the whole file.

The method is written for a built skill. In a trial its words mean this:

| The method says | In a trial |
|---|---|
| `<skillDir>/design/overlay-kit` | `<skillDir>/overlay-kit` |
| `<skillDir>/design` | the draft's `design/`, the example's when it has none yet |
| the issue folder | `trials/NN/out` |
| the working folder | one per trial: `~/.local/share/overlay-kit/<skill>/trials-NN`, an absolute path, or the long video's own folder |
| `run.py hear "<clip>"` | `ae.py hear <skill> "<clip>"` |
| `run.py note` | `ae.py profile taste <skill> "<remark>"` |

## A format with paths

`ae.py variant <skill>` lists the paths. The order is fixed; only a path the person turned down in words is skipped. No path is
built without their choice, and `ae.py trial` without `--variant` refuses until there is one.

1. **A short probe of each path, on their video.** One clip, not the whole set, and the same stretch in every path, so they compare
   ways and not stretches. What a probe needs was asked in `phases/interview.md`. The tools of a path come first:
   `ae.py doctor --steps <the steps of the path being tried> --asr <provider>`, on their «да» (`phases/build.md`, §2); a path whose
   tools they refuse is said to be out, in one line.

   ```bash
   python "<skillDir>/tools/ae.py" trial <skill> "<source>" --variant <id>
   ```

   It leaves the draft as it is and leaves out what the catalog says a probe does not need. **One answer to `clips` serves every
   probe:** write it once, by `templates/format-skill/method/clips.md` and, when `bands` is among the paths, `clips-headline.md`, into
   one `ответы.json`, add the other questions of a path to the same file as they come, and pass it with `--answers` each time. Each
   path keeps its own trial folder. The speech is heard once and the next probes reuse it. A path that ends without a video (`reedit`)
   is made by hand as above, then `ae.py show <skill> "<file>" --variant <id>`.

   **A way of your own, offered beside the others or asked for after them, goes through the same probe,** in this order: set its steps
   and parameters in the draft (`ae.py profile set`); `ae.py variant <skill> --own <word>`;
   `ae.py trial <skill> "<source>" --variant own:<word>` with the same answers;
   `ae.py show <skill> "<file>" --variant own:<word>` if it ends without a video. It then stands on the dashboard beside the others. Turned down: `ae.py variant <skill> <id>` puts the draft on the path they chose, with their answers
   and the preset's steps.

2. **Show them side by side.** The dashboard already does. `ae.py ask choice --note "какой путь"` and one message:

   ```
   Вот оба способа на одном вашем отрывке, на дашборде рядом:
   1. Картинка целиком: <one line of what you see in it, the good and the bad>.
   2. Перемонтаж: <one line>.
   Какой берём? Если ни один, скажите, чего не хватает: попробую иначе.
   ```

   «Ни один» → what they say goes into the taste, you make a way of your own from it as in step 1, and show it again here, as many
   times as it takes.

3. **The choice.** `ae.py variant <skill> <id>` puts the draft on that path and keeps their answers so far. A way of your own they chose
   is already there, marked `own:<word>`: nothing to run, and it goes into `phases/refine.md`, «A new way». Then back to
   `phases/design.md`, «A format whose path is not chosen yet», for what the chosen path still lacks. Remarks on the probes
   go into the taste as usual.

4. **The full trial of the chosen path,** as above: without `--variant`, the whole set. Questions the path left open come first
   (`phases/interview.md`). Only its «да» goes on to the build.

## «Так нравится?»

When the clip is ready the dashboard already asks; say it in the chat too, with one line of what was
done (how much was cut, what was blurred, the drift). Then:

- **«Да»** → `ae.py verdict <skill> yes` → `phases/build.md`.
- **«Нет»** → `ae.py verdict <skill> no --note "<their words>"` and ask, in one message:

```
Что не нравится? Покажите, как надо и как не надо:
— что добавить, что убрать — и где (время в ролике, кадр, отрезок);
— пример, если есть: другой ролик, кадр, ссылка на то, как должно быть.
```

Every remark goes into the profile — `ae.py profile taste <skill> "<remark>" --video <trials/NN>` — and
what it changes goes into the parameters (`ae.py profile set …`). Say in one line what you changed, run
the trial again on the same piece, ask again. A remark you cannot turn into a parameter is still written
as taste: the format skill reads it.

## Checks before showing

The trial is shown only after the pipeline's own report says the drift is under 40 ms and, for a format
that cuts, no word was cut (the report's re-transcription check). A failed check is said as it is and
fixed in the profile — never hidden. A second look by a subagent is optional: `prompts/trial-check.md`.

A clip made by `reedit` has no such report from the pipeline. Its checks are the method's, on a probe too: `vertical-check`, the review
of its sheets, `vertical-final` with its measures, the finished file at full size. The words at the seams of `drop` are checked by you,
with `ae.py hear` on the finished clip, and you give the person those seconds to listen to: nothing else looks at them.

Next: `ae.py stage build`, read `phases/build.md`.

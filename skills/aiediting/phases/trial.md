# Trial edit

`ae.py stage trial`. The one edit the workshop makes: a piece of the person's source through the same
pipeline the format skill will run, to show. It loops until the person says «да» — there is no limit.

## Run

```bash
python "<skillDir>/tools/ae.py" trial <skill> "<source>" --start <S> --duration <D>
```

Pick a piece of 1–2 minutes that has what the format does (pauses for a lesson, a secret on screen for
a stream, a strong phrase for a vertical); a vertical may take the whole source. Camera and screen are
two files (separate tracks) → add `--screen "<screen file>"`: it is cut to the same piece. The result is in
`.aiediting-work/<skill>/trials/NN/out/` and on the dashboard.

**Exit code 3 — a decision is needed** (the plan, the cut list, the regions to blur, the clips). Read
`trials/NN/вопросы.json`, show it to the person in plain words (frames, times, the list), and write
their answer to `trials/NN/ответы.json` as `{"<key>": true}`, `{"<key>": false}` or
`{"<key>": {"ok": true, "payload": {...}}}` with what they changed. Then the same call with
`--answers trials/NN/ответы.json`. Never approve on their behalf.

A format with `graphics`: the trial is the base; put the graphics on it by `overlay-kit/README.md`, the
working folder for this piece kept until the «да». The clip shown is the one with graphics.

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

Next: `ae.py stage build`, read `phases/build.md`.

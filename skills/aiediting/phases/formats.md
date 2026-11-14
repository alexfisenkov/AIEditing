# Formats

`ae.py stage formats`. One question: which formats the person makes. Offer the list from
`<skillDir>/catalog/formats.json` with its one-line hints, and say plainly that their own formats are
welcome, through commas:

```
Какие форматы монтируем? Можно несколько, и свои — через запятую.
1. Эфир — почти не трогаем: точечный блюр секретного, громкость, .srt рядом.
2. Урок — вырезаем паузы и «э-э», главы плашками, .srt рядом.
3. Выпуск YouTube — паузы вон, главы плашками и таймкодами, план согласуется один раз.
4. Вертикаль (Reels, Shorts, TikTok) — 9:16, речь без пауз, вшитые субтитры; нарезка из длинного — ролики до 60 с.
5. Наложения — речь целиком, без склеек; поверх неё графика и настоящие экраны.
6. YouTube с графикой — чистая речь из дублей или цельная запись, поверх графика и настоящие экраны, правки маркерами.
7. Нарезка — из готового горизонтального ролика: вертикальные отрывки, два пути на выбор после пробы.
Например: «2, 4, подкаст».
```

`ae.py ask question --note "какие форматы"` before it goes out.

**The intro already answered it** (`ae.py intro`, `videos`) → not the open question again. Name the formats of the list that fit
their words, and their own words for the rest, in one line to confirm; the whole list only if they ask for it:

```
Вы говорили, что делаете уроки и Reels: значит, форматы «урок» и «вертикаль». Так и начнём, или добавить свои?
```

Beside this list the person can always hear the wider answer: AIEditing is a base of ways to edit, not a set menu. A format
named here is a start they can narrow to their niche, their task and their own design system. For example, a nail technician's
«нарезка» under the word `маникюр`: clips of 30 s because that is what their clients watch, hands and the result in the frame
rather than the speaker, their clients' words on screen, their own colours. It is the same paths with another profile and another
design, and the next person's `монтаж-*` shares nothing with it: `ae.py formats "маникюр" --like нарезка`.

## The answer

Pass it as it is: `python "<skillDir>/tools/ae.py" formats "<the answer>"`. It understands numbers,
words from the list and anything else as the person's own format, removes repeats, and drafts one
profile per format in `.aiediting-work/монтаж-<слово>/profile.json`. A refused answer (empty, a number
outside the list) → ask again in one line with the reason it printed.

- **The word is the person's.** «Подкаст» becomes `монтаж-подкаст`; «живой эфир» — `монтаж-живой-эфир`.
  Never translate or shorten it. A word that names an existing skill → ask whether this is a refinement.
- **An own format goes the same path** as a listed one: its draft starts from a neutral preset (pauses,
  loudness, `.srt`) and the interview shapes it like any other. Never skip a phase because it is «свой».
  An own word that wants another start: `ae.py formats "<word>" --preset overlay`.
- **An own word narrowed from a format of the list:** `ae.py formats "<word>" --like <that format>`. The draft is under their word and
  starts where that format starts. It has that format's paths: `ae.py variant`, `ae.py trial --variant` and `build-skill` work on it as
  on the original, and it is not built until a path is chosen. With `--preset` too, naming one of the paths, it has chosen that path.

## A format with paths

Some formats can be edited in very different ways. Each such way is a row under `variants` in `catalog/formats.json`, and
`ae.py formats` and `ae.py variant <skill>` print them. **You offer them; you do not pick for the person.** The question is one
message, in your own words, and it comes once you have seen their video: at the start of `phases/interview.md`. The probes on
their video are in `phases/trial.md`, and `build-skill` refuses such a format until a path is chosen.

A format with no `variants` goes as it always did. A way the catalog does not have and that fits this person: say so and offer
it beside the others (`phases/refine.md`, «A new way»).

## Order

Several formats → one at a time, through sources, interview, design, trial and build, then the next.
Say the order in one line («Начнём с урока, потом вертикаль») and let the person change it. The
dashboard shows all of them; the one in work is the one whose profile you are editing.

Next: `ae.py stage sources`, read `phases/sources.md`.

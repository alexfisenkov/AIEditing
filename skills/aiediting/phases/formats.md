# Formats

`ae.py stage formats`. One question: which formats the person makes. Offer the list from
`<skillDir>/catalog/formats.json` with its one-line hints, and say plainly that their own formats are
welcome, through commas:

```
Какие форматы монтируем? Можно несколько, и свои — через запятую.
1. Эфир — почти не трогаем: точечный блюр секретного, громкость, .srt рядом.
2. Урок — вырезаем паузы и «э-э», главы плашками, .srt рядом.
3. Выпуск YouTube — монтаж по частям с согласованием каждой, главы.
4. Вертикаль (Reels, Shorts, TikTok) — 9:16, речь без пауз, вшитые субтитры; нарезка из длинного — ролики до 60 с.
5. Наложения — речь целиком, без склеек; поверх неё графика и настоящие экраны.
Например: «2, 4, подкаст».
```

`ae.py ask question --note "какие форматы"` before it goes out.

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

## Order

Several formats → one at a time, through sources, interview, design, trial and build, then the next.
Say the order in one line («Начнём с урока, потом вертикаль») and let the person change it. The
dashboard shows all of them; the one in work is the one whose profile you are editing.

Next: `ae.py stage sources`, read `phases/sources.md`.

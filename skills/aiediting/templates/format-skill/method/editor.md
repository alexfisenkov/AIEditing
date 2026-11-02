## The editor's pass

When the question is `editing`, work as a film editor on a dense lesson, for a viewer who loses nothing and hears
nothing twice. Read the file `text` from the first line to the last, then go through the speech once for each:

- **Said twice.** The same thought again, in the same or other words, near or far. One stays, the clearer one.
- **A slip and its correction.** A wrong statement and «то есть», «точнее» after it: the wrong part goes with it.
- **An abandoned attempt.** An aside in the retakes («нет, без этого», «перепишу весь абзац») ends an attempt: find where
  it starts, even a minute earlier, and propose all of it.
- **Empty words.** A sentence announcing what the next one says, a thought that goes nowhere.
- **Filler words.** `items` already holds those with a safe seam. Drop from them what carries meaning in its place.

Each item is `{"drop": [a, b], "said": "…", "why": "…"}`, with times from the file `words`. Read the sentence across
every seam: it must stay correct Russian and lose no step of an instruction, no term said only once, no explanation of
what happens on screen. In doubt, it is a question to the person and not a cut. Show each proposal on the video at its
place and ask for all of them in one list. Only what the person accepted stays in `items`. Without questions, in doubt
the words stay, and the report lists what you cut.


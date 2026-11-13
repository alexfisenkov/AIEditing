## Inserts from their life

Where the pipeline has `broll`, it puts shots from the library under the literal meaning of a phrase, never «просто красиво». If nothing of theirs fits, the place goes to the re-shoot list, a free stock video or a graphic, or stays empty.

**Rules, all of them in the planner and in what you check.** Their own shot comes before a stock one. A horizontal frame gets horizontal inserts. The best stretch from the inventory, 3–6 s, not the start of the file. The joint is on a cut or at least 3 s away from it, never a sliver of the angle between. At most 2–3 in a row, then the person is in the frame again. The sound of an insert is off. A screen recording: a scheme with no action in it → the face; a program being talked about → the screen; a piece shorter than 1.5 s is a defect. A log shot without their LUT is named in the report; HDR video from a phone looks washed out in an SDR edit, so look at such an insert and say so in your last message.

**People.** Insert people from their photos without asking beforehand. When they say «этого замени», `run.py forbid "<who>"` and replace the insert; the list works from then on, in every skill of theirs.

**Approval.** In `plan` each insert is a line: time, phrase, what, from where, who is in the frame. Take a line out or set `"ok": false` in its answer; `want` is the text of a re-shoot line. In `auto` the proposal stands and each insert is a line of the report with who is in the frame.

**The re-shoot list** `досъёмка.md` in the issue folder: «time — phrase — what to shoot — seconds — orientation», short and easy to film. What they shoot goes into the library (`run.py library scan <kind>`), and the next run puts it in place; what is not shot stays stock or graphics.

**Stock** only by their own free key (`PEXELS_API_KEY`, `PIXABAY_API_KEY`, set by them in `.env`; never ask for it or print it): `run.py library stock "<query in English>" [--take N]`, two or three phrasings («morning coffee window», «pouring coffee closeup»), look in the library first. Choose what looks shot on a phone, not in a studio; no smiling people in an office. Check the licence allows free commercial use. A taken stock goes into the library with its source. Generating video or pictures never.

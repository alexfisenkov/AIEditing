## Clean speech

Before `run.py edit` make `clean-speech.mov` by `<skillDir>/design/overlay-kit/takes-and-markers.md`, in the folder
`~/.local/share/overlay-kit/<skill name>/<date>-<topic>-речь`, and pass it to `run.py edit` as the video. This format's way with a
recording is {{recording}}. The person's words for this video win: «только края», «цельная запись», «не резать» is `takes.py trim`;
«лучшие дубли», «вырежи паузы» is `takes.py plan`; «как есть», not even the edges, is the file itself to `run.py edit`, and the note
about clean speech in its report is then expected.

`speed` in its config is `params.speed` of `profile.json`, when it is there, and it only says in whose seconds the pieces and
the markers are: nothing there plays faster. `run.py edit` applies the speed, once, and the recogniser hears the speech before it. So
the finished video lasts `clean-speech.mov` ÷ `params.speed`, and the report says both lengths. A line «ДЛИНА НЕ СХОДИТСЯ» in it is
a defect, not a result, even though the run ended with code 0. The file with graphics takes the name of the recording:
`"<recording> - монтаж.mp4"`, not of `clean-speech`. Remarks as markers from an editor go by the same file: the cuts change the speech,
the scenes keep the seconds of the accepted video, and the result takes a new name.

A screen recorded apart does not go through `--screen` here, which works only with the step `motion`: its frames go into the scenes by
`overlay.py frames`, cut by the same pieces.


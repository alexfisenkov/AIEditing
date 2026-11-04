## Clean speech

The raw recordings hold repeats, silence and reading from a screen. Before everything else make the clean speech by
`<skillDir>/design/overlay-kit/takes-and-markers.md`, and pass its `clean-speech.mov` to `run.py edit` as the video. Remarks
as markers from an editor go by the same file: the cuts change the speech, the scenes keep the seconds of the accepted
video, and the result takes a new name. Set `speed` in its config from `params.speed` of `profile.json`, when it is there.


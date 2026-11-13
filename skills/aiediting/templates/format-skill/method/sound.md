## Voice, music and sounds

<!-- if voice_clean -->
**The voice** is cleaned by Auphonic on the person's own key before any cut, with the preset they chose by ear; the original sound stays beside it in `.звук/`. A missing or wrong key is told in a line: they put it into `.env` as `AUPHONIC_API_KEY` themselves; you never ask for the value or look at it. The same recording with the same preset is processed once. Another preset is a refinement.
<!-- end -->
<!-- if music -->
**Music** only from the folder or the service the profile names; nothing found means nothing is put in, and nothing is invented. 20 dB under the voice, a track for each chapter when the profile says so, the variants as separate files to choose by ear. You do not hear: say that the choice was by mood, tempo and measures, and offer the variants. Not to use: cheerful lo-fi, cartoon music, spa and nature sounds that are not the subject, a track with words under speech. A service without a developer access gives a list of tracks to download in `музыка-скачать.md`, mood and length by chapter; Epidemic Sound is connected through its own MCP server by its instructions, the key set by the person, and the code never downloads a track.
<!-- end -->
<!-- if music -->
**Sounds on the peak of the motion** when `params.sfx` has `roles`: the role follows the strength of the move (a soft whoosh for a small entrance, a big one for a big change, a tick for a counter, a hit for the title), and the peak of the sound goes on the peak of the motion, not on the start of the scene; `overlay.py peaks` reports the shift, and a miss of 6–9 frames is audible. Louder than the voice only a chapter title and a hit on a key word; a big whoosh about the voice; the rest 4–10 dB under it. Quiet on a change of angle, on typed letters and under an insert. Every visible insert that nothing covers has a sound; a chain of small appearances gets thin ticks. Adult sounds only. Theirs come first, then the kit's.
<!-- end -->
The result is at the loudness this format sets, `params.lufs` in `profile.json` (−16 LUFS when it names none), with a peak not above −1 dBFS: measure the finished file.

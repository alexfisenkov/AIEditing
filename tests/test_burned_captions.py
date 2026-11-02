"""Burned-in captions are built from spoken words only, as the .srt is: Scribe's spacing never makes a cue."""
import unittest

import _support  # noqa: F401  (puts the skill on sys.path)


def scribe_words(texts, start=0.0, step=0.4):
    """Words the way Scribe returns them after the contract: a spacing item between every two words."""
    out, t = [], start
    for i, text in enumerate(texts):
        if i:
            out.append({"text": " ", "start": round(t - 0.05, 3), "end": round(t, 3), "type": "spacing"})
        out.append({"text": text, "start": round(t, 3), "end": round(t + 0.3, 3), "type": "word"})
        t += step
    return out


class Captions(unittest.TestCase):
    def test_scribe_words_make_cues_of_up_to_four_words_and_no_empty_ones(self):
        from runtime.pipelines.captions import cues

        words = scribe_words(["сегодня", "мы", "соберём", "скилл", "монтажа", "для", "урока", "и", "эфира"])
        words.append({"text": "", "start": 3.7, "end": 3.8, "type": "word"})
        got = cues(words, {})
        self.assertTrue(got)
        for cue in got:
            self.assertTrue(cue["text"].strip(), cue)
            self.assertLessEqual(len(cue["text"].split()), 4, cue)
        self.assertEqual(" ".join(c["text"] for c in got),
                         "сегодня мы соберём скилл монтажа для урока и эфира")
        self.assertEqual([len(c["text"].split()) for c in got[:2]], [4, 4])

    def test_audio_events_and_fillers_are_not_captions(self):
        from runtime.pipelines.captions import cues

        words = scribe_words(["привет"]) + [{"text": "(смех)", "start": 0.5, "end": 0.9, "type": "audio_event"},
                                            {"text": "э-э", "start": 1.0, "end": 1.2, "type": "filler"}]
        self.assertEqual([c["text"] for c in cues(words, {})], ["привет"])

    def test_a_sentence_starts_with_a_capital_letter_and_a_clip_as_it_was_said(self):
        from runtime.pipelines.captions import cues

        words = scribe_words(["в", "этом", "суть.", "ну", "и", "ладно…", "пойдём", "дальше.", "iCloud", "тут."])
        self.assertEqual(" ".join(c["text"] for c in cues(words, {})), "в этом суть. Ну и ладно… пойдём дальше. iCloud тут.")

    def test_a_mark_on_its_own_joins_the_word_before_it_as_in_the_srt(self):
        """From the lesson: Scribe gives «.» as a word of no length, 6.6 s after «промпт»."""
        from runtime.pipelines.captions import cues

        words = [{"text": "промпт", "start": 1.0, "end": 1.4, "type": "word"}, {"text": ".", "start": 8.0, "end": 8.0, "type": "word"},
                 {"text": "отправляю", "start": 8.04, "end": 8.5, "type": "word"}]
        self.assertEqual([c["text"] for c in cues(words, {})], ["промпт.", "Отправляю"])
        self.assertEqual(cues(words[1:2], {}), [])

    def test_a_glossary_term_keeps_its_case_after_a_sentence_as_in_the_srt(self):
        from runtime.pipelines.captions import cues

        fixes = []
        got = cues(scribe_words(["Готово.", "нпм", "ставим."]), {"нпм": "npm"}, fixes)
        self.assertEqual(" ".join(c["text"] for c in got), "Готово. npm ставим.")
        self.assertEqual(fixes[0]["to"], "npm")


if __name__ == "__main__":
    unittest.main()

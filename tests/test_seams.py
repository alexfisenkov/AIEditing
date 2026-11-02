import unittest

import _support  # noqa: F401  (puts the skill on sys.path)


def said(text, step=0.4, length=0.34):
    return [{"text": w, "start": round(i * step, 3), "end": round(i * step + length, 3), "type": "word"}
            for i, w in enumerate(text.split())]


class Widened(unittest.TestCase):
    def test_the_cut_starts_right_after_the_word_before_it(self):
        """From the lesson: «с» of «соответственно» sounds at 1403.92, the recogniser starts the word at 1403.97."""
        from runtime.pipelines.seams import widened

        words = [{"text": "выберем,", "start": 1403.59, "end": 1403.91}, {"text": "соответственно,", "start": 1403.97, "end": 1404.31}]
        self.assertEqual(widened(words, [{"drop": [1403.97, 1404.31]}])[0]["drop"], [1403.92, 1404.31])

    def test_after_a_pause_it_takes_no_more_than_the_lead(self):
        from runtime.pipelines.seams import widened

        words = [{"text": "конец.", "start": 1.0, "end": 1.2}, {"text": "Ну,", "start": 3.0, "end": 3.2}]
        self.assertEqual(widened(words, [{"drop": [3.0, 3.2]}])[0]["drop"], [2.9, 3.2])

    def test_at_the_very_start_it_stays_inside_the_video(self):
        from runtime.pipelines.seams import widened

        self.assertEqual(widened([{"text": "Ну,", "start": 0.05, "end": 0.2}], [{"drop": [0.05, 0.2]}])[0]["drop"], [0.0, 0.2])


class WordlessInside(unittest.TestCase):
    def inner(self, keep, spans, gap=0.3):
        from runtime.pipelines.seams import wordless_inside

        return wordless_inside(keep, [{"start": a, "end": b, "text": "слово"} for a, b in spans], gap, 3.0)

    def test_a_grunt_between_two_words_goes_and_their_margins_stay(self):
        self.assertEqual(self.inner([(0.0, 5.0)], [(0.0, 1.0), (2.0, 3.0)]), [(1.12, 1.9), (3.12, 5.0)])

    def test_a_breath_before_the_first_word_goes(self):
        self.assertEqual(self.inner([(10.0, 12.0)], [(10.8, 12.0)]), [(10.0, 10.7)])

    def test_words_close_together_are_left_alone(self):
        self.assertEqual(self.inner([(0.0, 2.1)], [(0.0, 1.0), (1.2, 2.0)]), [])

    def test_a_long_stretch_may_be_a_demo(self):
        self.assertEqual(self.inner([(0.0, 10.0)], [(0.0, 1.0), (9.0, 10.0)]), [])

    def test_a_pause_shorter_than_the_margins_cuts_nothing(self):
        self.assertEqual(self.inner([(0.0, 2.3)], [(0.0, 1.0), (1.2, 2.3)], gap=0.2), [])


class Tidy(unittest.TestCase):
    def text(self, line, *cut):
        from runtime.pipelines.kept import kept_words
        from runtime.pipelines.seams import tidy
        from runtime.pipelines.timeline import subtract

        words = said(line)
        takes = [{"drop": [words[i]["start"], words[j]["end"]]} for i, j in cut]
        tidy(words, takes)
        left = kept_words(words, subtract([(0.0, 100.0)], [tuple(t["drop"]) for t in takes]))
        return " ".join(w["text"] for w in left)

    def test_the_comma_before_a_cut_filler_goes(self):
        self.assertEqual(self.text("вот можно, соответственно, здесь вычитать.", (2, 2)), "вот можно здесь вычитать.")

    def test_the_comma_stays_before_a_clause(self):
        self.assertEqual(self.text("можно увидеть, да, то есть он здесь.", (2, 2)), "можно увидеть, то есть он здесь.")

    def test_a_chain_of_fillers(self):
        self.assertEqual(self.text("от компании Anthropic, да, их, соответственно, приложения.", (3, 3), (5, 5)),
                         "от компании Anthropic их приложения.")

    def test_a_sentence_cut_to_its_end_leaves_a_full_stop(self):
        self.assertEqual(self.text("собирать эту систему и по этой системе тот текст собирать здесь. Вот сам открыл.", (3, 10)),
                         "собирать эту систему. Вот сам открыл.")
        self.assertEqual(self.text("если что-то не нравится, ну, или создать под себя. Дальше.", (4, 8)),
                         "если что-то не нравится. Дальше.")

    def test_a_whole_sentence_changes_nothing(self):
        self.assertEqual(self.text("Первое готово. Ненужная фраза. Дальше идем.", (2, 3)), "Первое готово. Дальше идем.")


if __name__ == "__main__":
    unittest.main()

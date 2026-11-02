import unittest

import _support  # noqa: F401  (puts the skill on sys.path)


class EndAfter(unittest.TestCase):
    def end(self, start, seconds, keep, longest=15.0):
        from runtime.pipelines.timeline import end_after

        return end_after(start, seconds, keep, longest)

    def test_nothing_cut(self):
        self.assertEqual(self.end(10.0, 4.0, [(0.0, 100.0)]), 14.0)

    def test_a_cut_under_it_moves_the_end(self):
        self.assertEqual(self.end(10.0, 4.0, [(0.0, 11.0), (13.0, 100.0)]), 16.0)

    def test_a_start_in_a_cut_counts_from_the_next_kept(self):
        self.assertEqual(self.end(10.0, 4.0, [(0.0, 5.0), (12.0, 100.0)]), 16.0)

    def test_no_further_than_longest(self):
        self.assertEqual(self.end(10.0, 4.0, [(0.0, 10.5), (40.0, 100.0)]), 25.0)

    def test_nothing_kept_after_it(self):
        self.assertEqual(self.end(10.0, 4.0, [(0.0, 5.0)]), 14.0)


class Flash(unittest.TestCase):
    def test_a_part_of_a_sentence_is_not_shown_for_a_moment(self):
        from runtime.media.srt_lines import lines

        text = "То есть для этого нужно будет перейти в настройки."
        tokens, at = [], 0.0
        for w in text.split():
            tokens.append({"text": w, "start": at, "end": at + 0.1})
            at += 0.3
        cues = [c["text"] for c in lines(tokens)]
        self.assertEqual(" ".join(cues), text)
        self.assertNotEqual(cues[0], "То есть")


if __name__ == "__main__":
    unittest.main()

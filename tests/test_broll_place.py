"""Where an insert may stand: 3–6 s, its edges on a cut or three seconds clear of one, no long runs, a usable piece of a file."""
import unittest

import _support  # noqa: F401  (puts the skill on sys.path)
from runtime.pipelines import broll_place as place


class Seams(unittest.TestCase):
    def test_seams_are_where_the_kept_spans_meet_in_the_cut_video(self):
        self.assertEqual(place.seams([(0.0, 10.0), (20.0, 35.0), (50.0, 60.0)]), [10.0, 25.0])
        self.assertEqual(place.seams([(0.0, 90.0)]), [])


class Fit(unittest.TestCase):
    def test_without_cuts_the_phrase_length_is_used_within_three_to_six(self):
        self.assertEqual(place.fit(12.0, 4.2, 20.0, [], 60.0), (12.0, 4.2))
        self.assertEqual(place.fit(12.0, 1.0, 20.0, [], 60.0), (12.0, 3.0))
        self.assertEqual(place.fit(12.0, 9.0, 20.0, [], 60.0), (12.0, 6.0))

    def test_the_clip_limits_the_length_and_one_under_three_seconds_is_no_insert(self):
        self.assertEqual(place.fit(12.0, 6.0, 4.0, [], 60.0), (12.0, 4.0))
        self.assertIsNone(place.fit(12.0, 4.0, 2.9, [], 60.0))

    def test_an_edge_on_a_cut_is_fine(self):
        self.assertEqual(place.fit(10.0, 4.0, 20.0, [10.0], 60.0), (10.0, 4.0))

    def test_an_edge_close_to_a_cut_snaps_to_it(self):
        self.assertEqual(place.fit(10.8, 4.0, 20.0, [10.0], 60.0), (10.0, 4.0))

    def test_an_edge_between_one_and_three_seconds_from_a_cut_is_refused(self):
        self.assertIsNone(place.fit(12.5, 4.0, 20.0, [10.0], 60.0))

    def test_an_edge_three_seconds_clear_is_fine(self):
        self.assertEqual(place.fit(13.0, 4.0, 20.0, [10.0], 60.0), (13.0, 4.0))

    def test_the_end_is_moved_onto_the_next_cut_when_it_would_fall_close_to_it(self):
        start, length = place.fit(20.0, 4.5, 20.0, [25.0], 60.0)
        self.assertEqual((start, round(start + length, 3)), (20.0, 25.0))

    def test_no_insert_runs_past_the_end_of_the_video(self):
        self.assertIsNone(place.fit(58.0, 4.0, 20.0, [], 60.0))
        self.assertEqual(place.fit(54.0, 4.0, 20.0, [], 60.0), (54.0, 4.0))


class Runs(unittest.TestCase):
    def slots(self, *starts, length=4.0):
        return [{"at": s, "len": length} for s in starts]

    def test_a_fourth_insert_in_a_row_is_dropped(self):
        kept = place.limit_run(self.slots(0, 4.5, 9, 13.5, 18), 3)
        self.assertEqual([s["at"] for s in kept], [0, 4.5, 9, 18])  # 18 follows a face: the dropped one left a gap

    def test_two_seconds_of_the_speaker_between_inserts_end_a_run(self):
        kept = place.limit_run(self.slots(0, 4.5, 9, 15.5, 20), 3)
        self.assertEqual([s["at"] for s in kept], [0, 4.5, 9, 15.5, 20])

    def test_a_run_limit_of_one_means_a_face_after_every_insert(self):
        kept = place.limit_run(self.slots(0, 4.5, 20, 24.5), 1)
        self.assertEqual([s["at"] for s in kept], [0, 20])


class Piece(unittest.TestCase):
    def test_a_photo_has_no_limit_but_the_phrase(self):
        self.assertEqual(place.piece_of({"type": "фото"}), (0.0, place.MAX_LEN))

    def test_a_clip_gives_its_best_stretch_at_least_three_seconds_long(self):
        row = {"type": "видео", "dur": 30.0, "best": [[2.0, 3.5], [10.0, 16.0]]}
        self.assertEqual(place.piece_of(row), (10.0, 6.0))

    def test_a_clip_without_best_stretches_is_taken_from_its_start(self):
        self.assertEqual(place.piece_of({"type": "видео", "dur": 20.0, "best": []}), (0.0, place.MAX_LEN))
        self.assertEqual(place.piece_of({"type": "видео", "dur": 4.0, "best": []}), (0.0, 4.0))

    def test_a_clip_shorter_than_three_seconds_or_of_unknown_length_is_no_candidate(self):
        self.assertIsNone(place.piece_of({"type": "видео", "dur": 2.0, "best": []}))
        self.assertIsNone(place.piece_of({"type": "видео", "dur": None, "best": []}))
        self.assertIsNone(place.piece_of({"type": "видео", "dur": 20.0, "best": [[1.0, 2.0]]}))


if __name__ == "__main__":
    unittest.main()

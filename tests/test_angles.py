"""The program of angles (R34) on made-up phrase boundaries: what a viewer sees, checked against the rules by hand."""
import unittest

import _support  # noqa: F401  (puts the skill on the path)

GAPS = [2.1, 3.7, 1.4, 4.6, 2.9, 5.3, 1.8, 3.2, 6.1, 2.4]  # seconds between phrase ends, an irregular speech


def boundaries(total):
    out, t, i = [], 0.0, 0
    while True:
        t = round(t + GAPS[i % len(GAPS)], 3)
        i += 1
        if t >= total:
            return out
        out.append(t)


def crops(plan):
    return [s for s in plan if s["camera"] == 0 and s["crop"] and s["crop"].get("to") is None and s["crop"]["zoom"] > 1]


class Rules(unittest.TestCase):
    def check_common(self, plan, total, points):
        self.assertEqual(plan[0]["start"], 0.0)
        self.assertAlmostEqual(plan[-1]["end"], total, places=3)
        for one, nxt in zip(plan, plan[1:]):
            self.assertAlmostEqual(one["end"], nxt["start"], places=6)
            self.assertIn(one["end"], points, "an angle changes only where a phrase ends or a cut is")
        for s in plan:
            self.assertGreaterEqual(s["end"] - s["start"], 3.0, s)
        first = plan[0]
        self.assertEqual(first["camera"], 0)
        self.assertGreater(first["crop"]["to"], first["crop"]["zoom"], "the opening pushes in")
        self.assertLessEqual(first["crop"]["to"] - first["crop"]["zoom"], 0.06, "barely noticeable")
        for s in crops(plan):
            self.assertLessEqual(s["end"] - s["start"], 12.0, s)
            self.assertAlmostEqual(s["crop"]["zoom"], 1.2)
            self.assertLess(s["crop"]["y"], 0.5, "the crop keeps air above the head")
        share = sum(s["end"] - s["start"] for s in crops(plan)) / total
        self.assertTrue(0.15 <= share <= 0.35, "about a quarter of the time in the crop: {:.2f}".format(share))

    def test_two_cameras(self):
        from runtime.pipelines.angles import program

        total = 300.0
        points = boundaries(total)
        plan = program(total, points, cameras=2)
        self.check_common(plan, total, points)
        side = [s for s in plan if s["camera"] != 0]
        self.assertGreaterEqual(len(side), 3, "the side camera is used, rarely")
        for s in side:
            self.assertTrue(3.0 <= s["end"] - s["start"] <= 10.0, s)
        for one, nxt in zip(side, side[1:]):
            self.assertGreaterEqual(nxt["start"] - one["start"], 60.0, "not more than once a minute")
        self.assertEqual(plan, program(total, points, cameras=2), "the same speech, the same program")

    def test_one_camera_crops_and_pushes_only(self):
        from runtime.pipelines.angles import program

        total = 120.0
        points = boundaries(total)
        plan = program(total, points, cameras=1)
        self.check_common(plan, total, points)
        self.assertTrue(all(s["camera"] == 0 for s in plan))

    def test_side_only_where_that_camera_was_running(self):
        from runtime.pipelines.angles import program

        total = 300.0
        plan = program(total, boundaries(total), cameras=2, cover={1: [(100.0, 200.0)]})
        side = [s for s in plan if s["camera"] == 1]
        self.assertTrue(side)
        self.assertTrue(all(100.0 <= s["start"] and s["end"] <= 200.0 for s in side), side)

    def test_nowhere_to_change_is_one_angle(self):
        from runtime.pipelines.angles import program

        plan = program(8.0, [], cameras=2)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["camera"], 0)


if __name__ == "__main__":
    unittest.main()

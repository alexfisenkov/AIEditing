"""Vertical pipeline: stack from «screen + window», clips from a long recording, native vertical, captions,
music only from the person's library, three platform files."""
import importlib.util
import unittest

from _support import TempDirCase, ffmpeg, needs_ffmpeg
from test_blur_static import gray_frame
from test_pipelines_helpers import Approver, asr_config, profile, sha
from test_vertical_media import screen_with_window

OUT = (1080, 1920)
HAVE_PIL = importlib.util.find_spec("PIL") is not None
WINDOW = {"x": 1000, "y": 460, "w": 240, "h": 240}


def long_words(seconds):
    """A phrase of four words every 3 s; a question every fifth phrase."""
    words, t, k = [], 0.5, 0
    while t + 2.6 < seconds:
        for i in range(4):
            last = i == 3
            text = "слово{}".format(k * 4 + i) + (("?" if k % 5 == 0 else ".") if last else "")
            words.append({"text": text, "start": round(t + i * 0.6, 2), "end": round(t + i * 0.6 + 0.5, 2)})
        t, k = t + 3.0, k + 1
    return {"words": words}


@needs_ffmpeg
class Vertical(TempDirCase):
    def test_screen_and_window_become_a_stack(self):
        from runtime import pipelines
        from runtime.media import probe

        src = screen_with_window(self.tmp / "экран.mp4", duration=3.0)
        asr = asr_config(self.tmp, {"words": [{"text": "привет", "start": 0.5, "end": 1.0}]})
        prof = profile(["vertical", "loudnorm"], asr, layout="screen_face_window", face=WINDOW, lufs=-14)
        approve = Approver()
        report = pipelines.run(src, prof, self.tmp / "выпуск", approve)
        self.assertIn("vertical", approve.asked)
        info = probe(report["output"])
        self.assertEqual((info["width"], info["height"]), OUT)
        rows = gray_frame(report["output"], 1.5, OUT)
        self.assertLess(abs(rows[300][100] - 96), 20)
        self.assertGreater(rows[1500][540], 220)
        self.assertTrue(any("мягкое лицо" in n for n in report["notes"]), report["notes"])

    def test_long_recording_offers_scored_clips_cut_at_phrase_ends(self):
        from runtime import pipelines
        from runtime.media import probe

        seconds = 150.0
        src = self.tmp / "длинное.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=gray:s=320x180:r=25:d={}".format(seconds),
               "-f", "lavfi", "-i", "sine=f=440:d={}".format(seconds), "-c:v", "libx264", "-preset",
               "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(src))
        words = long_words(seconds)
        ends = {w["end"] for w in words["words"] if w["text"][-1] in ".?"}
        starts = {w["start"] for i, w in enumerate(words["words"]) if i % 4 == 0}
        seen = {}

        def choose(payload):
            seen["items"] = [dict(i) for i in payload["items"]]
            payload["chosen"] = [payload["items"][1]["id"]]

        prof = profile(["vertical"], asr_config(self.tmp, words), layout="face_full",
                       face={"x": 120, "y": 40, "w": 80, "h": 100}, max_seconds=60, clips=[5, 10])
        report = pipelines.run(src, prof, self.tmp / "выпуск", Approver(edits={"clips": choose}))
        items = seen["items"]
        self.assertTrue(5 <= len(items) <= 10, len(items))
        for item in items:
            self.assertIn(item["end"], ends, "a clip ends where a phrase ends")
            self.assertIn(item["start"], starts)
            self.assertLessEqual(item["end"] - item["start"], 60)
            self.assertTrue(item["said"].startswith("слово"))
            self.assertIn("total", item["why"])
        self.assertEqual(sorted(i["score"] for i in items)[::-1], [i["score"] for i in items], "best first")
        pick = items[1]
        info = probe(report["output"])
        self.assertEqual((info["width"], info["height"]), OUT)
        self.assertAlmostEqual(info["duration"], pick["end"] - pick["start"], delta=0.2)
        self.assertEqual([c["id"] for c in report["clips"]], [pick["id"]])

    @unittest.skipUnless(HAVE_PIL, "Pillow not installed (ae.py doctor installs it)")
    def test_native_vertical_with_captions_music_note_and_exports(self):
        from runtime import pipelines
        from runtime.media import probe

        src = self.tmp / "снято вертикально.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=0x808080:s=540x960:r=25:d=3",
               "-f", "lavfi", "-i", "sine=f=440:d=3",
               "-vf", "drawbox=x=0:y=0:w=40:h=960:color=white:t=fill", "-c:v", "libx264", "-preset",
               "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(src))
        before = sha(src)
        words = {"words": [{"text": "Привет", "start": 0.2, "end": 0.8}, {"text": "всем.", "start": 0.9, "end": 2.6}]}
        steps = ["vertical", "plate", "overlay_png", "music", "loudnorm", "export_platforms"]
        prof = profile(steps, asr_config(self.tmp, words), captions="burned", lufs=-14, music=None)
        out = self.tmp / "выпуск"
        report = pipelines.run(src, prof, out, Approver())
        info = probe(report["output"])
        self.assertEqual((info["width"], info["height"]), OUT)
        rows = gray_frame(report["output"], 1.5, OUT)
        self.assertGreater(rows[960][20], 200, "not reframed: the stripe is still at the left edge")
        band = [rows[y][x] for y in range(1000, 1300, 4) for x in range(200, 880, 4)]
        self.assertGreater(max(band), 225, "white caption letters in the lower middle")
        self.assertLess(min(band), 90, "on a dark caption plate")
        self.assertTrue(any("Без музыки" in n for n in report["notes"]))
        self.assertIn("Без музыки", report["report"].read_text(encoding="utf-8"))
        self.assertEqual(sorted(p.name.rsplit("-", 1)[-1] for p in report["exports"]),
                         ["reels.mp4", "shorts.mp4", "tiktok.mp4"])
        self.assertTrue(all(p.parent == out.resolve() for p in report["exports"]))
        self.assertEqual(sha(src), before)

    def test_music_comes_from_the_library_folder(self):
        from runtime import pipelines

        lib = self.tmp / "музыка" / "спокойная"
        lib.mkdir(parents=True)
        ffmpeg("-f", "lavfi", "-i", "sine=f=220:d=2", str(lib / "трек.wav"))
        src = screen_with_window(self.tmp / "экран.mp4", duration=3.0)
        asr = asr_config(self.tmp, {"words": []})
        prof = profile(["vertical", "music"], asr, layout="screen_face_window", face=WINDOW,
                       music={"dir": str(self.tmp / "музыка"), "mood": "спокойная"})
        report = pipelines.run(src, prof, self.tmp / "выпуск", Approver())
        self.assertFalse(any("Без музыки" in n for n in report["notes"]), report["notes"])


if __name__ == "__main__":
    unittest.main()

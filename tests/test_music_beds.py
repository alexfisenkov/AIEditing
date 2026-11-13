"""Music from the person's own folder: by chapters, in variants, 20 dB under the voice; nothing there, nothing laid."""
import re
import subprocess

from _support import TempDirCase, ffmpeg, needs_ffmpeg
from runtime.pipelines import music


class Ctx:
    """The part of a run's context the music step reads."""

    def __init__(self, outdir, params, chapters=(), duration=6.0, keep=None):
        self.params, self.outdir, self.chapters = params, outdir, list(chapters)
        self.keep = keep or [(0.0, duration)]
        self.pieces, self.notes, self.music = None, [], {}
        self.info = {"duration": duration, "has_audio": True}

    def p(self, name, default=None):
        value = self.params.get(name)
        return default if value is None else value

    def note(self, text):
        self.notes.append(text)

    def has(self, step):
        return step == "music"


def tone(path, freq, seconds=8.0):
    ffmpeg("-f", "lavfi", "-i", "sine=f={}:d={}:sample_rate=48000".format(freq, seconds), "-c:a", "pcm_s16le", str(path))
    return path


def band_level(path, start, length, freq):
    """Mean volume (dB) of a narrow band around `freq` in [start, start + length]."""
    done = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-ss", str(start), "-t", str(length), "-i", str(path), "-af",
                           "bandpass=f={}:width_type=h:w=60,volumedetect".format(freq), "-f", "null", "-"],
                          capture_output=True, text=True)
    return float(re.search(r"mean_volume: (-?[\d.]+) dB", done.stderr).group(1))


class Plan(TempDirCase):
    def test_no_folder_and_no_tracks_lay_nothing_and_raise_nothing(self):
        for params in ({}, {"music": {"dir": str(self.tmp / "нет такой")}}, {"music": {"dir": str(self.tmp)}}):
            ctx = Ctx(self.tmp / "out", params)
            music.plan_music(ctx)
            self.assertEqual(ctx.music, {}, params)
            self.assertFalse((self.tmp / "out" / music.TO_FETCH).exists())

    def test_a_chosen_service_without_tracks_leaves_a_list_to_download(self):
        out = self.tmp / "out"
        ctx = Ctx(out, {"music": {"service": "epidemic", "dir": str(self.tmp / "музыка"), "mood": "спокойная",
                                  "per_chapter": True}},
                  chapters=[{"start": 0.0, "title": "Начало"}, {"start": 90.0, "title": "Как это сделать"}], duration=200.0)
        music.plan_music(ctx)
        self.assertEqual(ctx.music, {})
        text = (out / music.TO_FETCH).read_text(encoding="utf-8")
        self.assertIn("Начало", text)
        self.assertIn("Как это сделать", text)
        self.assertIn("1:30", text)   # the second chapter is 110 s long and starts at 1:30
        self.assertIn("1:50", text)
        self.assertIn("спокойная", text)

    def test_chapters_and_variants_come_from_the_profile(self):
        folder = self.tmp / "музыка"
        folder.mkdir()
        for name in ("a.wav", "b.wav", "c.wav"):
            (folder / name).write_bytes(b"RIFF")
        ctx = Ctx(self.tmp / "out", {"music": {"dir": str(folder), "per_chapter": True, "variants": 2}},
                  chapters=[{"start": 0.0, "title": "А"}, {"start": 3.0, "title": "Б"}], duration=6.0)
        music.plan_music(ctx)
        self.assertEqual([p.name for p in ctx.music["tracks"]], ["a.wav", "b.wav", "c.wav"])
        self.assertEqual(ctx.music["chapters"], [3.0])
        self.assertEqual(ctx.music["variants"], 2)
        self.assertEqual(ctx.music["db"], -20.0)


@needs_ffmpeg
class Mix(TempDirCase):
    def test_each_chapter_has_its_track_and_every_variant_is_a_file(self):
        folder = self.tmp / "музыка"
        folder.mkdir()
        tone(folder / "1-низкий.wav", 300)
        tone(folder / "2-высокий.wav", 1500)
        video = self.tmp / "в.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s=160x90:r=25:d=6", "-f", "lavfi", "-i",
               "anullsrc=r=48000:cl=mono", "-t", "6", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-shortest", str(video))
        out = self.tmp / "out"
        ctx = Ctx(out, {"music": {"dir": str(folder), "per_chapter": True, "variants": 2}},
                  chapters=[{"start": 0.0, "title": "А"}, {"start": 3.0, "title": "Б"}], duration=6.0)
        music.plan_music(ctx)
        done = music.mix(video, ctx.music, [], -16.0, self.tmp / "смесь.mp4")
        self.assertGreater(band_level(done, 0.5, 1.5, 300), band_level(done, 0.5, 1.5, 1500) + 10)
        self.assertGreater(band_level(done, 4.0, 1.5, 1500), band_level(done, 4.0, 1.5, 300) + 10)
        beds = sorted(p.name for p in (out / music.VARIANTS).iterdir())
        self.assertEqual(beds, ["вариант-1.m4a", "вариант-2.m4a"])
        second = out / music.VARIANTS / "вариант-2.m4a"
        self.assertGreater(band_level(second, 0.5, 1.5, 1500), band_level(second, 0.5, 1.5, 300) + 10)

    def test_an_accent_by_role_lands_its_peak_on_the_plate(self):
        import json

        own = self.tmp / "звуки"
        (own / "pop").mkdir(parents=True)
        # 0.4 s of near silence with a 20 ms burst at 0.2 s: the catalog says its peak is at 200 ms
        ffmpeg("-f", "lavfi", "-i", "aevalsrc='if(between(t,0.19,0.21),0.9*sin(2*PI*800*t),0.001*sin(2*PI*800*t))':s=48000:d=0.4",
               "-c:a", "pcm_s16le", str(own / "pop" / "a.wav"))
        (own / "catalog.json").write_text(json.dumps({"sounds": [
            {"role": "pop", "file": "pop/a.wav", "dur_ms": 400, "peak_ms": 200, "level_db": -1.0}]}), encoding="utf-8")
        video = self.tmp / "в.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s=160x90:r=25:d=4", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
               "-t", "4", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(video))
        ctx = Ctx(self.tmp / "out", {"sfx": {"roles": True, "dir": str(own), "db": 0}}, duration=4.0)
        music.plan_music(ctx)
        done = music.mix(video, ctx.music, [2.0], -16.0, self.tmp / "акцент.mp4")
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(done), "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                             capture_output=True).stdout
        import array

        pcm = array.array("h")
        pcm.frombytes(raw[: len(raw) // 2 * 2])
        loudest = max(range(len(pcm)), key=lambda i: abs(pcm[i])) / 8000.0
        self.assertAlmostEqual(loudest, 2.0, delta=0.03)

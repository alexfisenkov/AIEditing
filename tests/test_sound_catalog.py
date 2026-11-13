"""Sound catalog of any folder (the kit's or the person's own): role, length and the moment of the peak, measured."""
import json
import math
import random
import struct
import sys
import unittest
import wave

from _support import SKILL, TempDirCase, needs_ffmpeg

KIT_TOOLS = SKILL / "overlay-kit" / "tools"
if str(KIT_TOOLS) not in sys.path:
    sys.path.insert(0, str(KIT_TOOLS))

from overlaylib import sfxcat, sounds  # noqa: E402

RATE = 16000


def burst_wav(path, seconds=1.0, at=0.62, width=0.04, rate=RATE):
    """Quiet noise with one loud burst `width` long starting at `at`: the envelope peaks inside the burst."""
    rnd = random.Random(7)
    frames = []
    for i in range(int(seconds * rate)):
        t = i / rate
        loud = at <= t < at + width
        amp = 0.8 if loud else 0.02
        frames.append(int(32767 * amp * math.sin(2 * math.pi * 900 * t) + rnd.uniform(-80, 80)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", max(-32768, min(32767, f))) for f in frames))


@needs_ffmpeg
class Build(TempDirCase):
    def test_the_peak_is_the_maximum_of_the_envelope_and_the_length_is_the_files(self):
        burst_wav(self.tmp / "звуки" / "hit" / "мой-удар.wav", seconds=1.0, at=0.62, width=0.04)
        cat = sfxcat.build(self.tmp / "звуки")
        self.assertEqual(len(cat["sounds"]), 1)
        row = cat["sounds"][0]
        self.assertEqual(row["role"], "hit")
        self.assertEqual(row["file"], "hit/мой-удар.wav")
        self.assertAlmostEqual(row["dur_ms"], 1000, delta=5)
        self.assertGreaterEqual(row["peak_ms"], 615)
        self.assertLessEqual(row["peak_ms"], 665)
        self.assertAlmostEqual(row["level_db"], 20 * math.log10(0.8), delta=0.6)

    def test_roles_come_from_folders_and_old_names_and_the_rest_is_left_out(self):
        burst_wav(self.tmp / "s" / "whoosh-big" / "a.wav", seconds=0.3, at=0.1)
        burst_wav(self.tmp / "s" / "pop-soft.wav", seconds=0.2, at=0.05)
        burst_wav(self.tmp / "s" / "mouse-click.wav", seconds=0.2, at=0.05)
        burst_wav(self.tmp / "s" / "boom.wav", seconds=0.2, at=0.05)
        burst_wav(self.tmp / "s" / "not-a-role" / "b.wav", seconds=0.2, at=0.05)
        cat = sfxcat.build(self.tmp / "s")
        got = {(r["role"], r["file"]) for r in cat["sounds"]}
        self.assertEqual(got, {("whoosh-big", "whoosh-big/a.wav"), ("pop", "pop-soft.wav"), ("click", "mouse-click.wav")})
        self.assertEqual(sorted(sfxcat.left_out(self.tmp / "s")), ["boom.wav", "not-a-role/b.wav"])

    def test_write_puts_catalog_json_beside_the_sounds(self):
        burst_wav(self.tmp / "s" / "tick" / "t.wav", seconds=0.2, at=0.05)
        path = sfxcat.write(self.tmp / "s")
        self.assertEqual(path, self.tmp / "s" / "catalog.json")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), sfxcat.build(self.tmp / "s"))

    def test_the_command_writes_the_catalog_and_names_what_has_no_role(self):
        import contextlib
        import io

        import overlay

        burst_wav(self.tmp / "s" / "tick" / "t.wav", seconds=0.2, at=0.05)
        burst_wav(self.tmp / "s" / "boom.wav", seconds=0.2, at=0.05)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = overlay.main(["sfxcat", str(self.tmp / "s")])
        self.assertEqual(code, 0)
        self.assertTrue((self.tmp / "s" / "catalog.json").is_file())
        self.assertIn("tick 1", out.getvalue())
        self.assertIn("boom.wav", out.getvalue())

    def test_the_shipped_catalog_is_what_the_files_measure(self):
        sfx = SKILL / "overlay-kit" / "template" / "public" / "sfx"
        shipped = json.loads((sfx / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(shipped, sfxcat.build(sfx))


def row(role, file, peak=40, dur=300):
    return {"role": role, "file": file, "dur_ms": dur, "peak_ms": peak, "level_db": -3.0}


class Manifest(TempDirCase):
    def work(self):
        work = self.tmp / "work"
        (work / "src" / "data").mkdir(parents=True)
        return work

    def test_roles_list_the_persons_own_sounds_first_and_only_files_that_exist(self):
        work = self.work()
        sfx = work / "public" / "sfx"
        burst_wav(sfx / "hit" / "hit-01.ogg.wav", seconds=0.1, at=0.02)  # any audio file will do
        burst_wav(sfx / "own" / "hit" / "mine.wav", seconds=0.1, at=0.02)
        (sfx / "catalog.json").write_text(json.dumps({"sounds": [
            row("hit", "hit/hit-01.ogg.wav", peak=50), row("hit", "hit/missing.ogg"), row("pop", "pop/gone.ogg")]}), encoding="utf-8")
        (sfx / "own" / "catalog.json").write_text(json.dumps({"sounds": [row("hit", "hit/mine.wav", peak=70)]}), encoding="utf-8")
        data = sounds.write_manifest(work)
        self.assertEqual([(s["file"], s["peak_ms"]) for s in data["roles"]["hit"]],
                         [("sfx/own/hit/mine.wav", 70), ("sfx/hit/hit-01.ogg.wav", 50)])
        self.assertNotIn("pop", data["roles"])
        self.assertEqual(json.loads((work / "src" / "data" / "sfx.json").read_text(encoding="utf-8")), data)

    @needs_ffmpeg
    def test_own_role_folders_are_copied_and_measured(self):
        import contextlib
        import io

        work = self.work()
        (work / "public" / "sfx").mkdir(parents=True)
        mine = self.tmp / "мои звуки"
        burst_wav(mine / "whoosh" / "свист.wav", seconds=0.5, at=0.3)
        burst_wav(mine / "tick.wav", seconds=0.2, at=0.05)
        with contextlib.redirect_stdout(io.StringIO()):
            copied, ignored = sounds.add_sfx(work, mine)
        self.assertEqual((copied, ignored), (2, 0))
        data = sounds.write_manifest(work)
        self.assertEqual(data["files"]["tick"], "sfx/tick.wav")
        first = data["roles"]["whoosh"][0]
        self.assertEqual(first["file"], "sfx/own/whoosh/свист.wav")
        self.assertGreaterEqual(first["peak_ms"], 295)
        self.assertEqual(data["roles"]["tick"][0]["file"], "sfx/own/tick.wav")

    def test_the_templates_manifest_carries_the_roles_of_the_shipped_catalog(self):
        template = SKILL / "overlay-kit" / "template"
        data = json.loads((template / "src" / "data" / "sfx.json").read_text(encoding="utf-8"))
        shipped = json.loads((template / "public" / "sfx" / "catalog.json").read_text(encoding="utf-8"))["sounds"]
        self.assertEqual(sum(len(v) for v in data["roles"].values()), len(shipped))
        self.assertEqual(data["roles"]["pop"][0]["file"], "sfx/pop-soft.wav")


class Roles(unittest.TestCase):
    def test_the_role_list_is_the_one_in_the_kit(self):
        source = (SKILL / "overlay-kit" / "template" / "src" / "kit" / "Sound.tsx").read_text(encoding="utf-8")
        for role in sfxcat.ROLES:
            self.assertIn('"{}"'.format(role), source, role)
        self.assertTrue(set(sfxcat.OLD_ROLE) == set(sounds.NAMES))
        self.assertTrue(set(sfxcat.OLD_ROLE.values()) <= set(sfxcat.ROLES))


if __name__ == "__main__":
    unittest.main()

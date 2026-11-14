"""The intro is kept and laid where it belongs; what the interview chose is proved by a fact; the pace of shorts only in shorts."""
import io
import json
import os
import sys
from contextlib import redirect_stdout
from unittest import mock

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))


class Base(TempDirCase):
    def setUp(self):
        super().setUp()
        self.work, self.home = self.tmp / "work", self.tmp / "home"
        self.home.mkdir()
        env = {"AIEDITING_WORK": str(self.work), "AIEDITING_NO_SERVE": "1", "HOME": str(self.home),
               "USERPROFILE": str(self.home), "LOCALAPPDATA": str(self.home / "local"),
               "AIEDITING_LIBRARY": str(self.tmp / "нет-библиотеки")}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("AUPHONIC_API_KEY", None)
        here = os.getcwd()
        os.chdir(str(self.tmp))
        self.addCleanup(os.chdir, here)
        self.ae("init", "--title", "Проба")

    def ae(self, *args, code=0):
        from aelib.cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            got = main([str(a) for a in args])
        self.assertEqual(got, code, buf.getvalue())
        return buf.getvalue()

    def state(self):
        from state import read

        return read(self.work)

    def library(self):
        from runtime.library.paths import make_layout

        lib = self.tmp / "библиотека"
        lib.mkdir()
        make_layout(lib)
        os.environ["AIEDITING_LIBRARY"] = str(lib)
        return lib

    def draft(self, skill="монтаж-урок"):
        return json.loads((self.work / skill / "profile.json").read_text(encoding="utf-8"))


class Intro(Base):
    def test_answers_are_kept_and_survive_a_fresh_start(self):
        self.ae("intro", "set", "blog=про ремонт, для новичков", "camera=телефон, петличка")
        self.assertEqual(self.state()["intro"]["blog"], "про ремонт, для новичков")
        self.ae("init", "--fresh", "--title", "Заново")
        self.assertEqual(self.state()["intro"]["camera"], "телефон, петличка")
        self.assertIn("про ремонт", self.ae("intro"))

    def test_an_unknown_key_is_refused(self):
        self.assertIn("ключи", self.ae("intro", "set", "pets=кот", code=1))

    def test_a_new_draft_gets_the_taste_from_the_intro(self):
        self.ae("intro", "set", "blog=про ремонт", "liked=/видео/хороший.mp4", "disliked=ролик с музыкой громче голоса")
        out = self.ae("formats", "урок")
        notes = [t["note"] for t in self.draft()["taste"]]
        self.assertIn("Из знакомства, блог и зритель: про ремонт", notes)
        self.assertIn("Из знакомства, нравится по монтажу: /видео/хороший.mp4", notes)
        self.assertIn("Из знакомства, не нравится по монтажу: ролик с музыкой громче голоса", notes)
        self.assertIn("из знакомства", out)
        self.ae("intro", "apply", "монтаж-урок")  # once is enough: nothing doubled
        self.assertEqual(len(self.draft()["taste"]), 3)

    def test_without_intro_a_draft_is_as_before(self):
        self.ae("formats", "урок")
        self.assertEqual(self.draft().get("taste") or [], [])

    def test_with_a_library_the_facts_go_to_its_files(self):
        lib = self.library()
        self.ae("intro", "set", "blog=про ремонт", "camera=телефон, петличка", "forbid=лицо сына; адрес дома")
        self.ae("intro", "apply")
        self.assertIn("про ремонт", (lib / "обо-мне" / "блог.md").read_text(encoding="utf-8"))
        self.assertIn("телефон, петличка", (lib / "обо-мне" / "кто-я.md").read_text(encoding="utf-8"))
        never = (lib / "чего-нельзя.md").read_text(encoding="utf-8")
        self.assertIn("лицо сына", never)
        self.assertIn("адрес дома", never)
        self.ae("intro", "apply")
        self.assertEqual((lib / "обо-мне" / "блог.md").read_text(encoding="utf-8").count("про ремонт"), 1)


class Proofs(Base):
    def setUp(self):
        super().setUp()
        self.ae("formats", "урок")

    def check(self, *values):
        if values:
            self.ae("profile", "set", "монтаж-урок", *values)
        return self.ae("profile", "check", "монтаж-урок")

    def test_nothing_new_nothing_to_prove(self):
        self.assertNotIn("Не доказано", self.check())

    def test_inserts_without_a_library(self):
        out = self.check('steps=["speech_spans","cut_spans","broll"]', "params.broll=true")
        self.assertIn("broll: библиотека не подключена", out)

    def test_inserts_with_an_empty_library(self):
        self.library()
        out = self.check('steps=["speech_spans","cut_spans","broll"]', "params.broll=true")
        self.assertIn("в описи библиотеки нет ни одного файла", out)

    def test_music_from_a_folder_that_is_not_there(self):
        out = self.check('steps=["speech_spans","cut_spans","music"]', "params.music={}".format(
            json.dumps({"dir": str(self.tmp / "нет")}, ensure_ascii=False)))
        self.assertIn("music: папки с треками нет", out)

    def test_music_from_a_folder_with_a_track_is_proved(self):
        folder = self.tmp / "музыка"
        folder.mkdir()
        (folder / "трек.mp3").write_bytes(b"x")
        out = self.check('steps=["speech_spans","cut_spans","music"]', "params.music={}".format(
            json.dumps({"dir": str(folder)}, ensure_ascii=False)))
        self.assertNotIn("Не доказано", out)

    def test_a_voice_without_its_key(self):
        out = self.check('steps=["voice_clean","speech_spans","cut_spans"]')
        self.assertIn("voice_clean: ключа нет в переменной AUPHONIC_API_KEY", out)
        self.assertNotIn("=", out.split("voice_clean:", 1)[1].split("\n", 1)[0].replace("<", ""))

    def test_cameras_without_a_trial_of_them(self):
        out = self.check('steps=["speech_spans","cut_spans","angles"]')
        self.assertIn("angles: ни одна проба", out)
        report = self.work / "монтаж-урок" / "trials" / "01" / "out" / "отчёт.md"
        report.parent.mkdir(parents=True)
        report.write_text("Сдвиг по звуку относительно главной камеры: камера-2 +0.120 с\n", encoding="utf-8")
        self.assertNotIn("angles:", self.check())

    def test_build_names_what_is_not_proved(self):
        self.ae("profile", "set", "монтаж-урок", 'steps=["speech_spans","cut_spans","broll"]', "params.broll=true")
        out = self.ae("build-skill", self.work / "монтаж-урок" / "profile.json", self.tmp / "out")
        self.assertIn("Собран:", out)
        self.assertIn("broll: библиотека не подключена", out)


class PaceOfShorts(TempDirCase):
    def method(self, preset):
        from aelib import skillmd

        profile = json.loads((SKILL / "templates" / "profiles" / (preset + ".json")).read_text(encoding="utf-8"))
        return skillmd._method(profile)

    def test_only_formats_with_short_or_vertical_clips_get_it(self):
        for preset in ("lesson", "stream", "youtube"):
            self.assertNotIn("Pace and shorts", self.method(preset), preset)
        for preset in ("vertical", "repurpose", "repurpose-reedit"):
            self.assertIn("Pace and shorts", self.method(preset), preset)
        self.assertNotIn("<!--", self.method("lesson"))


if __name__ == "__main__":
    import unittest

    unittest.main()

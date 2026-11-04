"""Paths of a format, the re-edit as one of them, and a workshop that stays open to any editing skill."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

from _support import SKILL, TempDirCase, make_av, needs_ffmpeg
from test_pipelines_helpers import Approver, asr_config, profile
from test_vertical_source import horizontal

sys.path.insert(0, str(SKILL / "tools"))

AE = SKILL / "tools" / "ae.py"
PRESETS = SKILL / "templates" / "profiles"
CATALOG = json.loads((SKILL / "catalog" / "formats.json").read_text(encoding="utf-8"))["formats"]
STEPS = json.loads((SKILL / "catalog" / "steps.json").read_text(encoding="utf-8"))["steps"]
needs_pillow = unittest.skipUnless(importlib.util.find_spec("PIL"), "нет Pillow: путь с полями его требует")


def draft_of(word, **changes):
    from aelib.formats import parse_answer
    from aelib.profiles import new_profile

    return dict(new_profile(parse_answer(word)[0]), **changes)


def said(start, count, step=2.0):
    return [{"text": "слово{}{}".format(i, "." if i % 5 == 4 else ""), "start": start + i * step,
             "end": start + i * step + step - 0.1} for i in range(count)]


class Catalog(unittest.TestCase):
    def test_a_format_with_paths_brings_them_and_the_others_do_not_change(self):
        from aelib.formats import parse_answer

        cut, lesson = parse_answer("нарезка, урок")
        self.assertEqual([v["id"] for v in cut["variants"]], ["bands", "reedit"])
        self.assertEqual(sorted(lesson), ["custom", "id", "preset", "skill", "title", "word"])
        self.assertEqual(sorted(parse_answer("подкаст")[0]), ["custom", "id", "preset", "skill", "title", "word"])

    def test_every_path_is_a_preset_of_known_steps_that_passes_the_schema(self):
        from aelib import variants
        from runtime.profile import check_profile

        for fmt in CATALOG:
            rows = fmt.get("variants") or []
            self.assertEqual(len({r["id"] for r in rows}), len(rows), fmt["word"])
            if rows:
                self.assertEqual(rows[0]["preset"], fmt["preset"], "the format's own start is its first path")
            for row in rows:
                for key in ("id", "title", "hint", "preset"):
                    self.assertTrue(row.get(key), "{}: {}".format(row, key))
                preset = json.loads((PRESETS / (row["preset"] + ".json")).read_text(encoding="utf-8"))
                self.assertEqual([s for s in preset["steps"] if s not in STEPS], [], row["id"])
                self.assertEqual(check_profile(variants.switched(draft_of(fmt["word"]), row)), [], row["id"])
                self.assertEqual(check_profile(variants.switched(draft_of(fmt["word"]), row, short=True)), [], row["id"])

    def test_a_new_path_is_a_row_and_a_preset_with_no_code(self):
        from aelib import variants

        extra = {"id": "whole", "title": "Целиком", "hint": "как есть", "preset": "overlay"}
        table = [{"id": "x", "word": "свой", "title": "Свой", "preset": "repurpose",
                  "variants": [{"id": "bands", "title": "б", "hint": "б", "preset": "repurpose"}, extra]}]
        prof = dict(draft_of("нарезка"), format="свой")
        with mock.patch("aelib.variants.load_formats", return_value=table):
            self.assertEqual(variants.by_id(prof, "whole"), extra)
            self.assertEqual(variants.switched(prof, extra)["steps"], ["write_srt", "graphics"])


class Paths(unittest.TestCase):
    def test_the_reedit_preset_says_what_the_format_needs(self):
        preset = json.loads((PRESETS / "repurpose-reedit.json").read_text(encoding="utf-8"))
        self.assertEqual(preset["steps"], ["reedit"])
        params = preset["params"]
        self.assertEqual((params["cta_lead"], params["cta_tail"], params["safe"]), (2.0, 4.0, "reels"))
        self.assertNotIn("music", params, "no bed is built on this path")
        self.assertEqual(sorted(params["cta_parts"]), ["after", "before", "lead", "word"])
        for key in ("speed", "source_speed", "max_seconds", "clips", "cta", "covers"):
            self.assertIn(key, params)

    def test_the_step_needs_what_graphics_needs(self):
        self.assertEqual(STEPS["reedit"]["tools"], STEPS["graphics"]["tools"])

    def test_the_schema_refuses_a_broken_value(self):
        from runtime.profile import check_profile

        self.assertTrue(check_profile(draft_of("нарезка", params={"covers": "много"})))
        self.assertTrue(check_profile(draft_of("нарезка", params={"cta_parts": {"слово": "УРОК"}})))
        self.assertEqual(check_profile(draft_of("нарезка", params={"covers": 12, "cta_parts": {"word": "УРОК"}})), [])
        self.assertEqual(check_profile(draft_of("нарезка", params={"cta_parts": None, "source_speed": None})), [])

    def test_answers_go_along_and_what_only_the_old_path_had_defaults_goes(self):
        from aelib import variants

        prof = draft_of("нарезка")
        prof["params"].update(speed=1.12, cta="Напишите «УРОК»")
        row = variants.by_id(prof, "reedit")
        on = dict(variants.switched(prof, row), variant="reedit")
        self.assertEqual(on["steps"], ["reedit"])
        self.assertEqual((on["params"]["speed"], on["params"]["cta"]), (1.12, "Напишите «УРОК»"))
        self.assertNotIn("layout", on["params"], "nothing of the fields stays in a re-edit")
        self.assertNotIn("variant", prof, "the draft itself is not touched")
        back = variants.switched(on, variants.by_id(on, "bands"))
        self.assertEqual(back["params"]["speed"], 1.12)
        self.assertIn("teaser", back["steps"])

    def test_a_short_probe_is_one_clip_and_leaves_the_rest_out(self):
        from aelib import variants

        prof = draft_of("нарезка")
        short = variants.switched(prof, variants.by_id(prof, "bands"), short=True)
        self.assertNotIn("teaser", short["steps"])
        self.assertEqual(short["params"]["clips"], [1, 1])
        reedit = variants.switched(prof, variants.by_id(prof, "reedit"), short=True)
        self.assertEqual((reedit["params"]["clips"], reedit["params"]["covers"]), ([1, 1], 0))

    def test_only_a_format_with_paths_and_no_choice_is_stopped(self):
        from aelib.variants import unchosen

        self.assertIn("не выбран", unchosen(draft_of("нарезка")))
        self.assertIn("не выбран", unchosen(draft_of("нарезка", variant="нет-такого")))
        self.assertIsNone(unchosen(draft_of("нарезка", variant="reedit")))
        self.assertIsNone(unchosen(draft_of("нарезка", variant="own:кружок")))
        self.assertIsNone(unchosen(draft_of("урок")))
        self.assertIsNone(unchosen(draft_of("подкаст")))


class Workshop(TempDirCase):
    def setUp(self):
        super().setUp()
        self.home = self.tmp / "дом"
        self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home), AIEDITING_NO_SERVE="1",
                        AIEDITING_WORK=str(self.tmp / "work"))

    def ae(self, *args, ok=True):
        proc = subprocess.run([sys.executable, str(AE), *map(str, args)], capture_output=True, text=True, encoding="utf-8",
                              env=self.env, cwd=str(self.tmp))
        if ok:
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc

    def draft(self, skill):
        return self.tmp / "work" / skill / "profile.json"

    def begin(self, word="нарезка", *more):
        self.ae("init", "--mode", "new", "--title", "проба")
        return self.ae("formats", word, *more)


class Choosing(Workshop):
    def test_the_paths_are_printed_and_no_path_builds_until_one_is_chosen(self):
        out = self.begin().stdout
        self.assertIn("путь bands", out)
        self.assertIn("путь reedit", out)
        refused = self.ae("build-skill", self.draft("монтаж-нарезка"), self.tmp / "out", ok=False)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("путь не выбран", refused.stdout)
        self.assertFalse((self.tmp / "out" / "монтаж-нарезка").exists())

    def test_choosing_moves_the_draft_onto_the_path(self):
        self.begin()
        self.assertIn("ещё ничего", self.ae("variant", "монтаж-нарезка").stdout)
        self.ae("profile", "set", "монтаж-нарезка", "params.speed=1.12")
        self.ae("variant", "монтаж-нарезка", "reedit")
        prof = json.loads(self.draft("монтаж-нарезка").read_text(encoding="utf-8"))
        self.assertEqual((prof["variant"], prof["steps"], prof["params"]["speed"]), ("reedit", ["reedit"], 1.12))

    def test_an_unknown_path_and_a_format_of_one_way_are_refused(self):
        self.begin("нарезка, урок")
        self.assertIn("Пути нет-такого нет", self.ae("variant", "монтаж-нарезка", "нет-такого", ok=False).stdout)
        self.assertIn("один путь", self.ae("variant", "монтаж-урок", "bands", ok=False).stdout)

    def test_a_way_of_ones_own_keeps_what_was_set_by_hand(self):
        self.begin()
        self.ae("profile", "set", "монтаж-нарезка", 'steps=["vertical"]')
        self.ae("variant", "монтаж-нарезка", "--own", "Кружок снизу")
        prof = json.loads(self.draft("монтаж-нарезка").read_text(encoding="utf-8"))
        self.assertEqual((prof["variant"], prof["steps"]), ("own:кружок-снизу", ["vertical"]))
        self.ae("build-skill", self.draft("монтаж-нарезка"), self.tmp / "out")

    def test_a_skill_built_before_paths_records_its_path_and_keeps_its_steps(self):
        self.begin()
        self.ae("profile", "set", "монтаж-нарезка", 'steps=["vertical","bands"]')
        self.ae("variant", "монтаж-нарезка", "bands", "--keep")
        prof = json.loads(self.draft("монтаж-нарезка").read_text(encoding="utf-8"))
        self.assertEqual((prof["variant"], prof["steps"]), ("bands", ["vertical", "bands"]))

    def test_a_start_that_names_a_path_has_chosen_it(self):
        self.begin("нарезка", "--preset", "repurpose-reedit")
        prof = json.loads(self.draft("монтаж-нарезка").read_text(encoding="utf-8"))
        self.assertEqual((prof["variant"], prof["steps"]), ("reedit", ["reedit"]))

    def test_a_narrow_skill_under_its_own_word_has_the_paths_of_its_format(self):
        out = self.begin("маникюр", "--like", "нарезка").stdout
        self.assertIn("монтаж-маникюр", out)
        self.assertIn("путь reedit", out)
        prof = json.loads(self.draft("монтаж-маникюр").read_text(encoding="utf-8"))
        self.assertEqual((prof["format"], prof["like"], prof["params"]["clips"]), ("маникюр", "нарезка", [5, 5]))
        self.assertIn("путь не выбран", self.ae("build-skill", self.draft("монтаж-маникюр"), self.tmp / "out", ok=False).stdout)
        self.assertIn("reedit", self.ae("variant", "монтаж-маникюр").stdout)
        self.ae("variant", "монтаж-маникюр", "reedit")
        self.ae("build-skill", self.draft("монтаж-маникюр"), self.tmp / "out")
        skill = self.tmp / "out" / "монтаж-маникюр"
        self.assertIn("## Re-edit", (skill / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((skill / "profile.json").read_text(encoding="utf-8"))["like"], "нарезка")

    def test_narrowing_from_a_format_with_one_way_or_none_at_all(self):
        self.begin("подкаст-про-урок", "--like", "урок")
        prof = json.loads(self.draft("монтаж-подкаст-про-урок").read_text(encoding="utf-8"))
        self.assertIn("cut_spans", prof["steps"])
        self.assertIn("один путь", self.ae("variant", "монтаж-подкаст-про-урок").stdout)
        self.ae("build-skill", self.draft("монтаж-подкаст-про-урок"), self.tmp / "out")
        self.assertIn("нет формата", self.ae("formats", "ещё", "--like", "нет-такого", ok=False).stdout)

    def test_a_start_naming_a_path_chooses_it_under_an_own_word_too(self):
        self.begin("маникюр", "--like", "нарезка", "--preset", "repurpose-reedit")
        prof = json.loads(self.draft("монтаж-маникюр").read_text(encoding="utf-8"))
        self.assertEqual((prof["variant"], prof["steps"]), ("reedit", ["reedit"]))

    def test_a_format_without_paths_has_no_new_field_and_builds_as_before(self):
        self.begin("урок")
        prof = json.loads(self.draft("монтаж-урок").read_text(encoding="utf-8"))
        self.assertNotIn("variant", prof)
        self.ae("build-skill", self.draft("монтаж-урок"), self.tmp / "out")
        text = (self.tmp / "out" / "монтаж-урок" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("## Re-edit", text)
        self.assertFalse((self.tmp / "out" / "монтаж-урок" / "design" / "overlay-kit").exists())


class Built(Workshop):
    def built(self, path):
        self.begin()
        self.ae("variant", "монтаж-нарезка", path)
        self.ae("build-skill", self.draft("монтаж-нарезка"), self.tmp / "out")
        return self.tmp / "out" / "монтаж-нарезка"

    def test_the_reedit_skill_carries_its_method_the_kit_and_the_tokens(self):
        skill = self.built("reedit")
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        for mark in ("## Re-edit", "## Clips from a finished video", "`reedit`", "and what «Re-edit» names",
                     "besides the working folder «Re-edit» names", "vertical-init", "vertical-check", "vertical-final",
                     "vertical-sheets", "--speech"):
            self.assertIn(mark, text)
        self.assertNotIn("{{", text)
        self.assertNotIn("## Graphics", text)
        self.assertTrue((skill / "design" / "overlay-kit" / "tools" / "overlay.py").is_file())
        self.assertTrue((skill / "design" / "overlay-kit" / ".from-aiediting").is_file())
        self.assertTrue((skill / "design" / "tokens.json").is_file())
        pins = json.loads((skill / "pins.json").read_text(encoding="utf-8"))
        self.assertTrue({"ffmpeg", "node", "remotion", "opencv-python", "numpy", "yunet-model"} <= set(pins["tools"]))
        check = subprocess.run([sys.executable, "-I", str(skill / "tools" / "run.py"), "check"], capture_output=True, text=True,
                               encoding="utf-8", cwd=str(self.tmp), env=self.env)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_the_bands_skill_has_neither_the_method_nor_the_kit(self):
        skill = self.built("bands")
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Clips from a finished video", text)
        self.assertIn('"headline": "…"', text)
        self.assertIn("When the question is `teaser`", text)
        self.assertNotIn("## Re-edit", text)
        self.assertNotIn("«Re-edit» names", text)
        self.assertFalse((skill / "design" / "overlay-kit").exists())

    def test_each_skill_is_told_only_of_the_secrets_it_can_close(self):
        reedit = (self.built("reedit") / "SKILL.md").read_text(encoding="utf-8")
        for absent in ("blur_track", "The `.srt`: a mistake", '"extra"', "`secrets`:", "goes under the blur"):
            self.assertNotIn(absent, reedit)
        self.assertIn("**Secrets on this path.**", reedit)
        self.assertIn("«Screens» in `vertical.md`", reedit)
        self.assertIn("`clips`:", reedit)
        self.assertIn("numbers the clips anew", reedit)
        self.assertNotIn("<!--", reedit)

    def test_a_skill_of_another_format_keeps_all_of_it(self):
        text = (self.built("bands") / "SKILL.md").read_text(encoding="utf-8")
        for mark in ("blur_track", "The `.srt`: a mistake", "`secrets`:"):
            self.assertIn(mark, text)
        self.assertNotIn("**Secrets on this path.**", text)
        self.assertNotIn("<!--", text)

    def test_the_reedit_skill_is_told_nothing_of_steps_it_does_not_have_and_no_whole_video(self):
        text = (self.built("reedit") / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn('"headline": "…"', text)
        self.assertNotIn("When the question is `teaser`", text)
        self.assertNotIn("then edits the whole video", text)
        self.assertIn("«План → готовые ролики»", text)
        self.assertIn("which may be the long video's own", text)


class KitChanges(Workshop):
    def kit(self):
        self.ae("init", "--mode", "new", "--title", "проба")
        self.ae("formats", "нарезка", "--preset", "repurpose-reedit")
        self.ae("build-skill", self.draft("монтаж-нарезка"), self.tmp / "out")
        design = self.tmp / "work" / "монтаж-нарезка" / "design"
        shutil.copytree(str(self.tmp / "out" / "монтаж-нарезка" / "design"), str(design), dirs_exist_ok=True)
        return design / "overlay-kit"

    def build_again(self, ok=True):
        return self.ae("build-skill", self.draft("монтаж-нарезка"), self.tmp / "out", "--replace", ok=ok)

    def test_a_kit_nobody_touched_renews_silently(self):
        kit = self.kit()
        (kit / "__pycache__").mkdir()
        (kit / "__pycache__" / "x.pyc").write_bytes(b"x")
        self.assertNotIn("правки", self.build_again().stdout)

    def test_a_changed_kit_stops_the_build_and_names_the_file_and_nothing_is_lost(self):
        kit = self.kit()
        (kit / "vertical.md").write_text("моя правка", encoding="utf-8")
        (kit / "моё.txt").write_text("своё", encoding="utf-8")
        out = self.build_again(ok=False)
        self.assertNotEqual(out.returncode, 0)
        for mark in ("vertical.md", "моё.txt", "ae.py kit"):
            self.assertIn(mark, out.stdout)
        self.assertEqual((kit / "vertical.md").read_text(encoding="utf-8"), "моя правка")

    def test_the_person_makes_it_their_own(self):
        kit = self.kit()
        (kit / "vertical.md").write_text("моя правка", encoding="utf-8")
        self.ae("kit", "монтаж-нарезка", "own")
        self.build_again()
        built = self.tmp / "out" / "монтаж-нарезка" / "design" / "overlay-kit"
        self.assertEqual((built / "vertical.md").read_text(encoding="utf-8"), "моя правка")
        self.assertFalse((built / ".from-aiediting").exists())
        self.build_again()

    def test_the_person_drops_it_for_the_current_one(self):
        kit = self.kit()
        (kit / "vertical.md").write_text("моя правка", encoding="utf-8")
        self.ae("kit", "монтаж-нарезка", "renew")
        self.build_again()
        built = self.tmp / "out" / "монтаж-нарезка" / "design" / "overlay-kit"
        self.assertNotEqual((built / "vertical.md").read_text(encoding="utf-8"), "моя правка")
        self.assertTrue((built / ".from-aiediting").is_file())

    def test_refining_says_it_before_the_build_does(self):
        self.ae("init", "--mode", "new", "--title", "проба")
        self.ae("formats", "нарезка", "--preset", "repurpose-reedit")
        self.ae("build-skill", self.draft("монтаж-нарезка"), self.tmp / "out")
        self.ae("install-skill", self.tmp / "out" / "монтаж-нарезка")
        kit = self.home / ".agents" / "skills" / "монтаж-нарезка" / "design" / "overlay-kit"
        (kit / "vertical.md").write_text("моя правка", encoding="utf-8")
        out = self.ae("profile", "open", "монтаж-нарезка", "--fresh").stdout
        self.assertIn("vertical.md", out)
        self.assertIn("ae.py kit", out)


class Handmade(Workshop):
    def written(self, name="монтаж-своё"):
        folder = self.home / ".agents" / "skills" / name
        (folder / "metod").mkdir(parents=True)
        (folder / "SKILL.md").write_text("---\nname: {}\n---\nстарое\n".format(name), encoding="utf-8")
        (folder / "metod" / "как.md").write_text("как я монтирую", encoding="utf-8")
        return folder

    def test_a_skill_written_by_hand_is_listed_opened_and_nothing_of_it_is_lost(self):
        folder = self.written()
        self.ae("init", "--mode", "refine", "--title", "проба")
        self.assertIn("монтаж-своё — без профиля", self.ae("list-skills").stdout)
        rows = json.loads(self.ae("list-skills", "--json").stdout)
        self.assertEqual([(r["name"], r["handmade"]) for r in rows], [("монтаж-своё", True)])
        out = self.ae("profile", "open", "монтаж-своё").stdout
        self.assertIn("Профиля у него нет", out)
        copy = self.tmp / "work" / "монтаж-своё" / "скилл" / "монтаж-своё"
        self.assertEqual((copy / "metod" / "как.md").read_text(encoding="utf-8"), "как я монтирую")
        (copy / "SKILL.md").write_text("---\nname: монтаж-своё\n---\nновое\n", encoding="utf-8")
        self.assertIn("в резерве", self.ae("install-skill", copy).stdout)
        self.assertIn("новое", (folder / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual((folder / "metod" / "как.md").read_text(encoding="utf-8"), "как я монтирую")
        self.ae("restore-skill", "монтаж-своё")
        self.assertIn("старое", (folder / "SKILL.md").read_text(encoding="utf-8"))

    def test_a_skill_that_lives_only_in_claude_skills_goes_back_there(self):
        folder = self.home / ".claude" / "skills" / "монтаж-своё"
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text("старое", encoding="utf-8")
        self.ae("init", "--mode", "refine", "--title", "проба")
        self.ae("profile", "open", "монтаж-своё")
        copy = self.tmp / "work" / "монтаж-своё" / "скилл" / "монтаж-своё"
        (copy / "SKILL.md").write_text("новое", encoding="utf-8")
        self.ae("install-skill", copy)
        self.assertEqual((folder / "SKILL.md").read_text(encoding="utf-8"), "новое")
        self.assertFalse((self.home / ".agents" / "skills" / "монтаж-своё").exists())

    def test_packages_left_out_of_the_copy_move_over_and_are_named(self):
        folder = self.written()
        packages = folder / "kit" / "node_modules" / "пакет"
        packages.mkdir(parents=True)
        (packages / "index.js").write_text("x", encoding="utf-8")
        self.ae("init", "--mode", "refine", "--title", "проба")
        self.ae("profile", "open", "монтаж-своё")
        copy = self.tmp / "work" / "монтаж-своё" / "скилл" / "монтаж-своё"
        self.assertFalse((copy / "kit" / "node_modules").exists())
        self.assertIn("kit/node_modules", self.ae("install-skill", copy).stdout)
        self.assertTrue((folder / "kit" / "node_modules" / "пакет" / "index.js").is_file())

    def test_a_copy_that_fails_leaves_the_skill_where_it_was(self):
        from aelib import handmade

        folder = self.written()
        copy = self.tmp / "копия" / "монтаж-своё"
        shutil.copytree(str(folder), str(copy))
        (copy / "SKILL.md").write_text("новое", encoding="utf-8")
        with mock.patch.dict(os.environ, self.env), mock.patch("aelib.handmade.shutil.copytree", side_effect=OSError("диск")), \
                mock.patch("aelib.paths.home", return_value=self.home):
            with self.assertRaises(OSError):
                handmade.install(copy)
        self.assertIn("старое", (folder / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual([p.name for p in folder.parent.iterdir()], ["монтаж-своё"])

    def built_and_installed(self):
        self.ae("init", "--mode", "new", "--title", "проба")
        self.ae("formats", "урок")
        self.ae("build-skill", self.draft("монтаж-урок"), self.tmp / "out")
        self.ae("install-skill", self.tmp / "out" / "монтаж-урок")
        return self.home / ".agents" / "skills" / "монтаж-урок"

    def test_what_a_built_skill_gained_later_survives_the_next_build(self):
        skill = self.built_and_installed()
        (skill / "notes").mkdir()
        (skill / "notes" / "моё.md").write_text("своё", encoding="utf-8")
        (skill / "design" / "method.md").write_text("## My own method\n\nкак монтирую я\n", encoding="utf-8")
        (skill / "design" / "overlay-kit").mkdir()
        (skill / "design" / "overlay-kit" / "своё.txt").write_text("своё", encoding="utf-8")
        out = self.ae("profile", "open", "монтаж-урок", "--fresh").stdout
        self.assertIn("notes", out)
        self.assertIn("design/overlay-kit", out)
        self.assertIn("design/method.md", out)
        self.assertNotIn("правили после сборки", out)
        self.ae("build-skill", self.draft("монтаж-урок"), self.tmp / "out2")
        again = self.tmp / "out2" / "монтаж-урок"
        self.assertEqual((again / "notes" / "моё.md").read_text(encoding="utf-8"), "своё")
        self.assertIn("## My own method", (again / "SKILL.md").read_text(encoding="utf-8"))
        self.assertTrue((again / "design" / "overlay-kit" / "своё.txt").is_file())

    def test_a_skill_md_edited_after_its_build_is_named_and_kept_aside(self):
        skill = self.built_and_installed()
        path = skill / "SKILL.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nмоя строка\n", encoding="utf-8")
        self.assertIn("правили после сборки", self.ae("profile", "open", "монтаж-урок", "--fresh").stdout)
        aside = self.tmp / "work" / "монтаж-урок" / "SKILL.как-установлен.md"
        self.assertIn("моя строка", aside.read_text(encoding="utf-8"))

    def test_an_own_file_cannot_replace_a_built_part(self):
        self.ae("init", "--mode", "new", "--title", "проба")
        self.ae("formats", "урок")
        own = self.tmp / "work" / "монтаж-урок" / "own"
        own.mkdir()
        (own / "SKILL.md").write_text("чужое", encoding="utf-8")
        self.assertNotEqual(self.ae("build-skill", self.draft("монтаж-урок"), self.tmp / "out", ok=False).returncode, 0)
        self.assertFalse((self.tmp / "out" / "монтаж-урок").exists())


@needs_ffmpeg
class Pipeline(TempDirCase):
    PARTS = {"lead": "Хотите урок?", "before": "Напишите", "word": "УРОК", "after": "— пришлю ссылку"}

    def answer(self, payload):
        payload["items"] = [{"id": "c01", "name": "1 — про дизайн?", "start": 5.0, "end": 45.0, "drop": [[15.0, 25.0]], "said": "проба"},
                            {"id": "c02", "name": "2", "start": 50.0, "end": 60.0, "said": "вторая"}]
        payload["chosen"] = ["c01"]

    def run_it(self, seconds=90, answer=None, **params):
        from runtime import pipelines

        src = horizontal(self.tmp / "готовый.mp4", seconds)
        params = dict(dict(cta_parts=self.PARTS), **params)
        prof = profile(["reedit"], asr_config(self.tmp, {"words": said(0.0, 44)}), vertical_source="clips", clips=[1, 2],
                       max_seconds=60, **params)
        self.approve = Approver(edits={"clips": answer or self.answer})
        return pipelines.run(src, prof, self.tmp / "выпуск", self.approve)

    def test_the_clips_are_asked_and_handed_over_and_no_video_is_made(self):
        report = self.run_it(speed=1.12, source_speed=1.07, covers=3)
        self.assertEqual(self.approve.asked, ["clips"])
        self.assertEqual(report["outputs"], [])
        self.assertIsNone(report["output"])
        self.assertIn("ролики ещё не собраны", report["handover"])
        issue = self.tmp / "выпуск"
        self.assertEqual(list(issue.glob("*.mp4")), [])
        data = json.loads((issue / "отрывки.json").read_text(encoding="utf-8"))
        self.assertEqual(data, {"rate": 1.12, "cta_lead": 2.0, "cta_tail": 4.0, "cta": self.PARTS, "safe": "reels",
                                "source_seconds": 90.0, "spans": {"c1": [[5.0, 15.0], [25.0, 45.0]]}, "names": {"c1": "1 — про дизайн"}})
        first = (issue / "слова-таймкоды.txt").read_text(encoding="utf-8").splitlines()[1]
        self.assertAlmostEqual(float(first[:7]), 2.0, delta=0.01, msg="seconds of the source, not of a finished clip")
        text = (issue / "отчёт.md").read_text(encoding="utf-8")
        self.assertIn("## Отрывки", text)
        self.assertIn("вынуто", text)
        self.assertIn("Речь выйдет на 1.20", text)

    def test_a_short_recording_is_one_clip_with_no_question(self):
        report = self.run_it(seconds=30)
        self.assertEqual(self.approve.asked, [])
        data = json.loads((self.tmp / "выпуск" / "отрывки.json").read_text(encoding="utf-8"))
        self.assertEqual(list(data["spans"]), ["c1"])
        self.assertEqual(data["names"]["c1"], "готовый-c1")
        self.assertEqual(data["safe"], "reels")
        self.assertIsNone(report["output"])

    def test_what_is_handed_over_passes_the_kits_own_check(self):
        kit = SKILL / "overlay-kit" / "tools"
        if not (kit / "overlaylib" / "vspans.py").is_file():
            self.skipTest("the kit's vertical set is not here yet")
        sys.path.insert(0, str(kit))
        from overlaylib import vspans

        self.run_it(speed=1.12)
        data = vspans.load(self.tmp / "выпуск" / "отрывки.json")
        self.assertEqual(vspans.clip_ids(data), ["c1"])

    def test_a_call_nobody_decided_is_refused_first(self):
        from runtime.pipelines.errors import PipelineError

        for undecided in ({"lead": " "}, {"lead": "", "before": "", "word": "", "after": ""}):
            with self.assertRaises(PipelineError) as caught:
                self.run_it(cta_parts=undecided)
            self.assertIn("«без призыва»", str(caught.exception))
            self.assertEqual(self.approve.asked, [])

    def test_a_said_no_call_goes_without_one_and_without_its_tail(self):
        self.run_it(cta_parts=None)
        data = json.loads((self.tmp / "выпуск" / "отрывки.json").read_text(encoding="utf-8"))
        self.assertIsNone(data["cta"])
        self.assertEqual((data["cta_lead"], data["cta_tail"]), (0.0, 0.0))

    def test_the_limit_is_the_whole_finished_clip_with_its_tail(self):
        from runtime.pipelines.context import Context
        from runtime.pipelines.vertical_source import stretches

        src = horizontal(self.tmp / "готовый.mp4", 200)
        for parts, expected in ((self.PARTS, (60 - 4) * 1.5), (None, 60 * 1.5)):
            prof = profile(["reedit"], asr_config(self.tmp, {"words": said(0.0, 95)}), vertical_source="clips", clips=[1, 3],
                           max_seconds=60, speed=1.5, cta_parts=parts)
            with mock.patch("runtime.pipelines.clips.candidates", return_value=[]) as found:
                stretches(Context(src, prof, self.tmp / "выпуск", Approver()))
            self.assertEqual(found.call_args.kwargs["max_s"], expected)

    def test_names_are_clean_and_case_does_not_tell_two_files_apart(self):
        from runtime.pipelines.errors import PipelineError
        from runtime.pipelines.reedit import _names

        ctx = types.SimpleNamespace(src=types.SimpleNamespace(stem="а:б?"))  # Path would read «а:» as a drive on Windows
        self.assertEqual(_names(ctx, [{"id": "c1"}]), {"c1": "а б -c1"})
        for one, other in (("Урок", "урок"), ("Урок?", "урок"), ("Зой", "Зой")):
            with self.assertRaises(PipelineError):
                _names(ctx, [{"id": "c1", "name": one}, {"id": "c2", "name": other}])

    def test_two_clips_of_the_fields_with_one_file_name_are_refused_before_one_replaces_the_other(self):
        from runtime import pipelines
        from runtime.pipelines.errors import PipelineError

        src = horizontal(self.tmp / "готовый.mp4", 90)
        prof = profile(["vertical", "bands"], asr_config(self.tmp, {"words": said(0.0, 44)}), vertical_source="clips",
                       layout={"kind": "native"}, clips=[1, 2], max_seconds=60)

        def answer(payload):
            payload["items"] = [{"id": "c1", "name": "Урок?", "start": 5.0, "end": 15.0, "said": "а"},
                                {"id": "c2", "name": "урок", "start": 20.0, "end": 30.0, "said": "б"}]
            payload["chosen"] = ["c1", "c2"]

        with self.assertRaises(PipelineError) as caught:
            pipelines.run(src, prof, self.tmp / "выпуск", Approver(edits={"clips": answer}))
        self.assertIn("одно имя", str(caught.exception))

    def test_steps_that_need_a_picture_are_refused_with_it(self):
        wide = horizontal(self.tmp / "готовый.mp4", 5)
        self.assertIn("blur_regions", self.refused(wide, steps=("reedit", "blur_regions")))

    def test_no_clip_chosen_is_refused(self):
        from runtime.pipelines.errors import PipelineError

        def none(payload):
            payload["chosen"] = []

        with self.assertRaises(PipelineError):
            self.run_it(answer=none)

    def test_two_clips_of_one_name_are_refused(self):
        from runtime.pipelines.errors import PipelineError

        def same(payload):
            self.answer(payload)
            payload["items"][1]["name"] = payload["items"][0]["name"]
            payload["chosen"] = ["c01", "c02"]

        with self.assertRaises(PipelineError) as caught:
            self.run_it(answer=same)
        self.assertIn("одно имя", str(caught.exception))

    def test_a_clip_longer_than_the_limit_is_noted(self):
        def long_one(payload):
            payload["items"] = [{"id": "c01", "start": 0.0, "end": 80.0}]
            payload["chosen"] = ["c01"]

        report = self.run_it(answer=long_one)
        self.assertTrue(any("рекомендованных params.max_seconds, но не запрет" in n for n in report["notes"]), report["notes"])

    def refused(self, video, steps=("reedit",), **params):
        from runtime import pipelines
        from runtime.pipelines.errors import PipelineError

        approve = Approver()
        with self.assertRaises(PipelineError) as caught:
            pipelines.run(video, profile(list(steps), asr_config(self.tmp, {"words": []}), cta_parts=self.PARTS, **params),
                          self.tmp / "выпуск", approve)
        self.assertEqual(approve.asked, [], "refused before any question")
        return str(caught.exception)

    def test_a_frame_that_is_not_wide_is_refused_first(self):
        tall = make_av(self.tmp / "вертикаль.mp4", [(1.0, 3.0)], 5.0, size="120x160")
        self.assertIn("16:9", self.refused(tall))

    def test_it_is_a_path_of_its_own(self):
        wide = horizontal(self.tmp / "готовый.mp4", 5)
        self.assertIn("bands", self.refused(wide, steps=("reedit", "vertical", "bands"), layout={"kind": "native"}))


@needs_ffmpeg
class Trial(Workshop):
    def setUp(self):
        super().setUp()
        self.src = horizontal(self.tmp / "готовый.mp4", 90)
        self.begin()
        self.ae("profile", "set", "монтаж-нарезка", "asr=" + json.dumps(asr_config(self.tmp, {"words": said(0.0, 44)})),
                'params.cta_parts={"word": "УРОК"}')

    def answers(self, name, chosen="c01"):
        path = self.tmp / name
        path.write_text(json.dumps({"vertical": True, "clips": {"ok": True, "payload": {
            "items": [{"id": "c01", "name": "первый", "start": 5.0, "end": 45.0, "headline": "ЗАГОЛОВОК", "said": "проба"}],
            "chosen": [chosen]}}}, ensure_ascii=False), encoding="utf-8")
        return path

    def test_a_trial_before_the_choice_is_refused_and_a_probe_is_not(self):
        out = self.ae("trial", "монтаж-нарезка", self.src, ok=False)
        self.assertEqual(out.returncode, 1)
        self.assertIn("путь не выбран", out.stdout)
        self.assertEqual(self.ae("trial", "монтаж-нарезка", self.src, "--variant", "reedit", ok=False).returncode, 3)

    def state(self):
        raw = (self.tmp / "work" / "state.js").read_text(encoding="utf-8")
        return json.loads(raw.split("=", 1)[1].strip().rstrip(";"))

    def probe_reedit(self, name="а1.json"):
        self.assertEqual(self.ae("trial", "монтаж-нарезка", self.src, "--variant", "reedit", ok=False).returncode, 3)
        done = self.ae("trial", "монтаж-нарезка", self.src, "--variant", "reedit", "--answers", self.answers(name))
        self.assertIn("ae.py show монтаж-нарезка", done.stdout)
        clip = make_av(self.tmp / "ролик.mp4", [(0.2, 1.0)], 1.5, size="180x320")
        self.ae("show", "монтаж-нарезка", clip, "--variant", "reedit")

    @needs_pillow
    def test_a_way_of_ones_own_is_probed_shown_beside_the_others_and_can_be_turned_down(self):
        self.ae("profile", "set", "монтаж-нарезка", 'steps=["reedit"]', "params.covers=2")
        self.ae("variant", "монтаж-нарезка", "--own", "кружок")
        answers = self.answers("свой.json")
        done = self.ae("trial", "монтаж-нарезка", self.src, "--variant", "own:кружок", "--answers", answers)
        self.assertIn("--variant own:кружок", done.stdout)
        clip = make_av(self.tmp / "ролик.mp4", [(0.2, 1.0)], 1.5, size="180x320")
        self.ae("show", "монтаж-нарезка", clip, "--variant", "own:кружок")
        self.ae("trial", "монтаж-нарезка", self.src, "--variant", "bands", "--answers", answers)
        rows = self.state()["trials"]
        self.assertEqual([(r["variant"], r["title"], r["probe"]) for r in rows],
                         [("own:кружок", "кружок", True), ("bands", "Картинка целиком", True)])
        self.ae("variant", "монтаж-нарезка", "bands")
        self.assertEqual([r["chosen"] for r in self.state()["trials"]], [False, True])
        prof = json.loads(self.draft("монтаж-нарезка").read_text(encoding="utf-8"))
        self.assertEqual(prof["variant"], "bands")
        self.assertIn("bands", prof["steps"])

    def test_someone_elses_own_word_is_not_a_path(self):
        self.assertEqual(self.ae("trial", "монтаж-нарезка", self.src, "--variant", "own:чужой", ok=False).returncode, 1)

    def test_a_re_edit_is_not_probed_on_a_piece(self):
        out = self.ae("trial", "монтаж-нарезка", self.src, "--variant", "reedit", "--start", "5", "--duration", "20", ok=False)
        self.assertEqual(out.returncode, 1)
        self.assertIn("--start", out.stdout)

    @needs_pillow
    def test_one_answer_serves_every_probe_and_each_path_has_its_own_folder(self):
        answers = self.answers("один.json")
        self.ae("trial", "монтаж-нарезка", self.src, "--variant", "bands", "--answers", answers)
        self.ae("trial", "монтаж-нарезка", self.src, "--variant", "reedit", "--answers", answers)
        trials = self.tmp / "work" / "монтаж-нарезка" / "trials"
        self.assertTrue((trials / "01" / "out" / "первый.mp4").is_file())
        self.assertTrue((trials / "02" / "out" / "отрывки.json").is_file())
        spans = json.loads((trials / "02" / "out" / "отрывки.json").read_text(encoding="utf-8"))
        self.assertEqual(spans["spans"], {"c1": [[4.9, 45.15]]}, "the same stretch, with the path's margins around its words")
        clip = make_av(self.tmp / "ролик.mp4", [(0.2, 1.0)], 1.5, size="180x320")
        self.ae("show", "монтаж-нарезка", clip, "--variant", "bands")
        self.assertTrue((trials / "01" / "ролик.mp4").is_file(), "a clip goes to the trial of its path")

    def test_a_probe_of_the_re_edit_hands_over_and_its_clip_goes_on_the_dashboard(self):
        self.probe_reedit()
        trials = self.tmp / "work" / "монтаж-нарезка" / "trials"
        self.assertTrue((trials / "01" / "out" / "отрывки.json").is_file())
        self.assertTrue((trials / "01" / "ролик.mp4").is_file())
        row = self.state()["trials"][0]
        self.assertEqual((row["n"], row["variant"], row["title"], row["probe"]), ("01", "reedit", "Перемонтаж под вертикаль", True))
        self.assertNotEqual((self.state().get("waiting") or {}).get("kind"), "trial", "a probe asks nothing by itself")

    @needs_pillow
    def test_a_probe_of_the_fields_is_one_clip_without_a_teaser_and_hears_nothing_twice(self):
        self.probe_reedit()
        self.assertEqual(self.ae("trial", "монтаж-нарезка", self.src, "--variant", "bands", ok=False).returncode, 3)
        trials = self.tmp / "work" / "монтаж-нарезка" / "trials"
        self.assertTrue(list((trials / "02" / "out" / ".расшифровка").glob("words-*.json")), "the speech is reused")
        done = self.ae("trial", "монтаж-нарезка", self.src, "--variant", "bands", "--answers", self.answers("а2.json"))
        self.assertIn("Проба пути", done.stdout)
        self.assertEqual([p.name for p in (trials / "02" / "out").glob("*.mp4")], ["первый.mp4"])
        rows = self.state()["trials"]
        self.assertEqual([(r["n"], r["variant"], r["probe"]) for r in rows], [("01", "reedit", True), ("02", "bands", True)])

    def test_the_choice_is_marked_and_a_probes_limit_is_not_an_answer(self):
        self.probe_reedit()
        self.ae("variant", "монтаж-нарезка", "reedit")
        self.assertEqual([r["chosen"] for r in self.state()["trials"]], [True])
        prof = json.loads(self.draft("монтаж-нарезка").read_text(encoding="utf-8"))
        self.assertEqual(prof["params"]["clips"], [5, 5])
        self.assertEqual(self.ae("trial", "монтаж-нарезка", self.src, ok=False).returncode, 3, "now the full trial runs")


class Texts(unittest.TestCase):
    def read(self, name):
        return (SKILL / name).read_text(encoding="utf-8")

    def test_the_parent_says_it_is_a_base_and_stays_open(self):
        text = " ".join(self.read("SKILL.md").split())
        self.assertIn("base of how a video can be edited", text)
        self.assertIn("own design system", text)
        self.assertIn("phases/refine.md", text)
        refine = " ".join(self.read("phases/refine.md").split())
        self.assertIn("written by hand", refine)
        self.assertIn("what no profile describes", refine.lower())

    def test_a_remark_on_any_re_edit_has_its_place(self):
        rows = [r for r in self.read("phases/refine.md").splitlines() if r.startswith("| ")]
        self.assertTrue(any("re-edit" in r and "overlay-kit/vertical.md" in r for r in rows))
        self.assertTrue(any("catalog/formats.json" in r for r in rows))

    def test_the_trial_shows_every_path_before_any_build(self):
        trial = self.read("phases/trial.md")
        for mark in ("--variant", "ae.py show", "ae.py variant", "A short probe of each path"):
            self.assertIn(mark, trial)
        self.assertIn("`build-skill` refuses", " ".join(self.read("phases/formats.md").split()))

    def test_the_dashboard_puts_probes_side_by_side(self):
        page = self.read("tools/state/dashboard.html")
        self.assertIn("t.probe", page)
        self.assertEqual(page.count("paths:"), 2, "both languages")

    def test_without_questions_the_choice_is_named(self):
        text = self.read("phases/no-questions.md")
        self.assertIn("you choose, and you say so", text)
        self.assertIn("ae.py variant", text)
        self.assertIn("--like нарезка", text)
        self.assertNotIn("the first row", text)
        self.assertIn("clips-headline.md", text)
        self.assertIn("video.band", text)
        self.assertIn("on any path but `reedit`", text)
        head = text.index("## 6.")
        self.assertNotIn("first in", text[text.index("## 3."):head].replace("from the top", ""))
        self.assertIn("in this order", text[head:])

    def test_the_menu_promises_only_what_is_built(self):
        for path in ("phases/formats.md", "catalog/formats.json", "templates/profiles/youtube.json"):
            self.assertNotIn("по частям", self.read(path), path)
            self.assertNotIn('"parts"', self.read(path), path)
        self.assertNotIn('approval="parts"', self.read("phases/interview.md"))

    def test_a_hum_is_not_taken_for_a_bed_by_itself(self):
        text = " ".join(self.read("templates/format-skill/method/reedit.md").split())
        self.assertNotIn("passes by itself", text)
        self.assertNotIn("You learn there is a bed", text)
        self.assertIn("it is not always a bed", text)
        self.assertIn(".c<N>.failed.mp4", text)
        for mark in ("vertical-words", "--overview", "`hidden`", "src/data/time-map.json", "src/data/face.json", "public/clips/source.mp4"):
            self.assertIn(mark, text)

    def test_the_trial_says_what_the_methods_words_mean_there(self):
        text = self.read("phases/trial.md")
        for mark in ("`trials/NN/out`", "trials-NN", "`ae.py profile taste", "--variant own:", "«Ни один»"):
            self.assertIn(mark, " ".join(text.split()))
        self.assertIn("~/.local/share/overlay-kit/", self.read("SKILL.md"))
        self.assertIn("--like", self.read("phases/formats.md"))

    def test_the_questions_the_format_lacked_are_asked(self):
        text = self.read("phases/interview.md")
        row = next(r for r in text.splitlines() if r.startswith("| A re-edit"))
        for mark in ("working folder", "clean speech", "safe zones", "covers", "call to action", "design", "`params.source_speed`"):
            self.assertIn(mark, row)
        self.assertNotIn("params.music", row)
        self.assertIn("where it comes from", self.read("phases/sources.md"))
        self.assertIn("What a probe needs is asked now", text)
        self.assertIn("params.cta_parts=null", text)
        self.assertNotIn("likely path", text)
        self.assertNotIn("not asked until", text)
        self.assertTrue(any(r.startswith("| Niche and audience") for r in text.splitlines()))

    def test_the_method_knows_all_four_cases_of_the_source(self):
        text = self.read("templates/format-skill/method/reedit.md")
        for mark in ("The folder exists", "a clean speech track", "with nothing under the speech", "with a bed under the speech",
                     "--hum-accepted", "Without the folder the scenes", "run.py\" hear"):
            self.assertIn(mark, text)
        self.assertNotIn("params.music", text)
        self.assertLess(text.index("design/sources.md"), text.index("The first question about this video"))

    def test_without_questions_finds_the_folder_and_the_call_first(self):
        text = self.read("phases/no-questions.md")
        self.assertIn("| Working folder of a long video", text)
        self.assertIn("| Call to action, before the recognition runs", text)
        self.assertLess(text.index("| Working folder of a long video"), text.index("you choose, and you say so"))

    def test_a_new_way_lives_in_the_source(self):
        text = " ".join(self.read("phases/refine.md").split())
        self.assertIn("npx skills update aiediting -g", text)
        self.assertIn("ae.py kit <skill> own", text)
        self.assertIn("маникюр", self.read("phases/formats.md"))

    def test_a_probe_has_its_own_checks_and_one_answer(self):
        text = " ".join(self.read("phases/trial.md").split())
        self.assertIn("One answer to `clips` serves every probe", text)
        self.assertIn("A clip made by `reedit` has no such report", text)
        self.assertIn("ae.py hear", text)
        self.assertIn("nobody installs it by that link", " ".join(self.read("phases/build.md").split()))
        self.assertIn("A format whose path is not chosen yet", self.read("phases/design.md"))


if __name__ == "__main__":
    unittest.main()

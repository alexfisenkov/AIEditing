"""«Без вопросов»: a confirmation is accepted, a judgement goes to the agent, a found secret is closed, all reported."""
import json
import subprocess
import sys
import unittest
import unittest.mock

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "templates" / "format-skill"))
from approvals import AutoApprover, FileApprover, NeedsApproval, approver_for  # noqa: E402

AE = SKILL / "tools" / "ae.py"


class Approver(TempDirCase):
    def test_a_confirmation_needs_nobody(self):
        self.assertTrue(AutoApprover(self.tmp)("srt", {"key": "srt", "draft": "x"}))
        self.assertFalse((self.tmp / "вопросы.json").exists())

    def test_a_moving_blur_is_looked_at_not_waved_through(self):
        with self.assertRaises(NeedsApproval):
            AutoApprover(self.tmp)("blur_track", {"key": "blur_track", "frames": []})

    def test_a_layout_nothing_could_tell_is_looked_at(self):
        with self.assertRaises(NeedsApproval):
            AutoApprover(self.tmp)("layout", {"key": "layout", "kind": None})
        self.assertTrue(AutoApprover(self.tmp)("layout", {"key": "layout", "kind": "face"}))

    def test_every_found_secret_with_a_place_is_closed(self):
        rect = {"x": 0, "y": 0, "w": 1, "h": 1}
        payload = {"key": "secrets", "candidates": [{"text": "почта", "blur": False, "rect": rect}, {"text": "ключ", "blur": False, "rect": rect}]}
        self.assertTrue(AutoApprover(self.tmp)("secrets", payload))
        self.assertEqual([c["blur"] for c in payload["candidates"]], [True, True])

    def test_an_answer_that_only_adds_areas_still_closes_what_was_found(self):
        (self.tmp / "ответы.json").write_text(json.dumps({"secrets": {"ok": True, "payload": {"extra": [{"x": 0}]}}}), encoding="utf-8")
        payload = {"key": "secrets", "candidates": [{"text": "почта", "blur": False, "rect": {"x": 0}}], "extra": []}
        self.assertTrue(AutoApprover(self.tmp)("secrets", payload))
        self.assertTrue(payload["candidates"][0]["blur"])
        self.assertEqual(payload["extra"], [{"x": 0}])

    def test_a_secret_said_aloud_is_not_called_closed(self):
        with self.assertRaises(NeedsApproval):
            AutoApprover(self.tmp)("secrets", {"key": "secrets", "candidates": [{"text": "номер", "blur": False}]})

    def test_a_judgement_stops_the_run_for_the_agent_not_the_person(self):
        with self.assertRaises(NeedsApproval) as seen:
            AutoApprover(self.tmp)("cards", {"key": "cards", "items": []})
        self.assertIn("решите сами", str(seen.exception))
        self.assertTrue((self.tmp / "вопросы.json").is_file())

    def test_the_agents_answer_is_used(self):
        (self.tmp / "ответы.json").write_text(json.dumps({"retakes": False, "secrets": {"ok": True, "payload": {"candidates": []}}}), encoding="utf-8")
        approve = AutoApprover(self.tmp)
        self.assertFalse(approve("retakes", {"key": "retakes", "items": []}))
        payload = {"key": "secrets", "candidates": [{"text": "почта", "blur": False}]}  # the agent's answer drops it
        self.assertTrue(approve("secrets", payload))
        self.assertEqual(payload["candidates"], [])

    def test_only_the_profile_or_the_run_switches_it_on(self):
        self.assertIsInstance(approver_for({"approval": "plan"}, self.tmp), FileApprover)
        self.assertNotIsInstance(approver_for({"approval": "plan"}, self.tmp), AutoApprover)
        self.assertIsInstance(approver_for({"approval": "auto"}, self.tmp), AutoApprover)
        self.assertIsInstance(approver_for({"approval": "plan"}, self.tmp, no_questions=True), AutoApprover)


class Workshop(TempDirCase):
    def ae(self, *args):
        env = dict(__import__("os").environ, AIEDITING_WORK=str(self.tmp / "work"), AIEDITING_NO_SERVE="1")
        return subprocess.run([sys.executable, str(AE), *args], capture_output=True, text=True, encoding="utf-8",
                              env=env, cwd=str(self.tmp))

    def test_init_remembers_the_mode_for_a_resumed_session(self):
        self.assertEqual(self.ae("init", "--mode", "new", "--no-questions", "--title", "проба").returncode, 0)
        self.assertIn('"noQuestions": true', (self.tmp / "work" / "state.js").read_text(encoding="utf-8"))

    def test_said_in_the_middle_the_draft_stays(self):
        self.ae("init", "--mode", "new", "--title", "проба")
        self.ae("formats", "подкаст")
        self.assertEqual(self.ae("no-questions").returncode, 0)
        self.assertIn('"noQuestions": true', (self.tmp / "work" / "state.js").read_text(encoding="utf-8"))
        self.assertTrue((self.tmp / "work" / "монтаж-подкаст" / "profile.json").is_file())

    def test_own_word_can_start_without_cuts(self):
        self.ae("init", "--mode", "new", "--title", "проба")
        out = self.ae("formats", "обращение", "--preset", "overlay")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        profile = json.loads((self.tmp / "work" / "монтаж-обращение" / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["steps"], ["write_srt", "graphics"])
        self.assertEqual(self.ae("profile", "set", "монтаж-обращение", "approval=auto").returncode, 0)

    def test_an_unknown_start_is_refused(self):
        self.ae("init", "--mode", "new", "--title", "проба")
        self.assertEqual(self.ae("formats", "обращение", "--preset", "нет-такой").returncode, 1)

    def test_a_start_cannot_silently_miss_a_draft_already_there(self):
        self.ae("init", "--mode", "new", "--title", "проба")
        self.ae("formats", "обращение")
        out = self.ae("formats", "обращение", "--preset", "overlay")
        self.assertEqual(out.returncode, 1)
        self.assertIn("profile set", out.stdout)

    def test_own_word_alone_keeps_the_neutral_start(self):
        self.ae("init", "--mode", "new", "--title", "проба")
        self.ae("formats", "подкаст")
        profile = json.loads((self.tmp / "work" / "монтаж-подкаст" / "profile.json").read_text(encoding="utf-8"))
        self.assertIn("cut_spans", profile["steps"])


class SecretsInTheReport(TempDirCase):
    def test_the_value_stays_out_of_what_is_reported(self):
        import types

        from runtime.pipelines import secrets

        notes = []
        ctx = types.SimpleNamespace(
            info={"duration": 10.0}, regions=[], candidates=[{"kind": "ключ", "text": "sk-настоящий", "start": 1.0, "end": 2.0,
                                                               "rect": {"x": 0, "y": 0, "w": 1, "h": 1}, "source": "ocr"},
                                                              {"kind": "почта", "text": "кто@где.рф", "start": 3.0, "end": 4.0}],
            ask=lambda key, q, payload: (True, {"candidates": [dict(c, blur=True) for c in payload["candidates"]], "extra": []}),
            note=notes.append, src=self.tmp / "a.mp4", work=self.tmp)
        with unittest.mock.patch.object(secrets, "_frame_count", return_value=5):
            secrets.plan_blur(ctx)
        self.assertEqual(ctx.regions[0]["what"], "ключ")
        seen = {}
        original = ctx.ask
        ctx.ask = lambda key, q, payload: (seen.update(payload), original(key, q, payload))[1]
        ctx.regions = []
        with unittest.mock.patch.object(secrets, "_frame_count", return_value=5):
            secrets.plan_blur(ctx)
        everything = json.dumps([ctx.regions, notes, seen], ensure_ascii=False)
        self.assertNotIn("sk-настоящий", everything)
        self.assertNotIn("кто@где.рф", everything)
        self.assertEqual(seen["candidates"][0]["text"], "sk-н…")


class Texts(unittest.TestCase):
    def test_the_rules_lead_to_the_phase_and_keep_the_limits(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        phase = (SKILL / "phases" / "no-questions.md").read_text(encoding="utf-8")
        self.assertIn("phases/no-questions.md", skill)
        for limit in ("published", "key is never asked", "paid"):
            self.assertIn(limit, phase.replace("A key", "a key").replace("Nothing paid", "paid"))
        self.assertNotIn("ae.py ask ", phase.replace("no `ae.py ask`", ""))


if __name__ == "__main__":
    unittest.main()

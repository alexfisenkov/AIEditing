import unittest

import _support  # noqa: F401  (puts the skill on sys.path)


def said(text, step=0.3):
    return [{"text": w, "start": round(i * step, 3), "end": round(i * step + 0.25, 3), "type": "word"}
            for i, w in enumerate(text.split())]


class Parasites(unittest.TestCase):
    def found(self, text, **kw):
        from runtime.pipelines.editing import find_parasites

        return [p["said"] for p in find_parasites(said(text, **kw))]

    def test_filler_words_set_off_by_commas(self):
        self.assertEqual(self.found("Claude сможет нам, соответственно, помочь, так сказать, с дизайном."),
                         ["соответственно,", "так сказать,"])

    def test_at_the_start_of_a_sentence(self):
        self.assertEqual(self.found("Первое готово. Ну, дальше смотрим настройки."), ["Ну,"])

    def test_a_word_doing_its_job_stays(self):
        for text in ("То есть это дообучаемый процесс.", "Это получается очень быстро.", "Да просто банально удобно.",
                     "Как бы вы это сделали?", "В общем чате это видно."):
            self.assertEqual(self.found(text), [], text)

    def test_no_air_no_cut(self):
        self.assertEqual(self.found("Нам, соответственно, помочь.", step=0.25), [])

    def test_what_a_take_already_cuts_is_skipped(self):
        from runtime.pipelines.editing import find_parasites

        words = said("Нам, соответственно, помочь.")
        self.assertEqual(find_parasites(words, [{"drop": [0.0, 1.0]}]), [])


class Pass(unittest.TestCase):
    def ctx(self, params, answer, folder):
        from pathlib import Path

        from runtime.pipelines.context import Context

        ctx = Context.__new__(Context)
        ctx.params, ctx.notes, ctx.work = dict(params), [], Path(folder)
        ctx.ask = answer
        return ctx

    def test_only_what_stays_in_the_answer_is_cut(self):
        import tempfile

        from runtime.pipelines.editing import plan_editing

        words = said("Claude сможет нам, соответственно, помочь с дизайном.")
        added = {"drop": [0.6, 1.2], "said": "нам, соответственно,", "why": "сказано дважды"}
        seen = {}

        def answer(key, question, payload):
            seen.update(payload, key=key)
            return True, {"items": [added, {"drop": "не время"}, "мусор"]}

        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.ctx({"editor": True}, answer, tmp)
            chosen = plan_editing(ctx, words, [])
            text = open(seen["text"], encoding="utf-8").read()
            table = open(seen["words"], encoding="utf-8").read()
        self.assertEqual(seen["key"], "editing")
        self.assertEqual(len(seen["items"]), 1)
        self.assertIn("Claude сможет нам", text)
        self.assertIn("0.000\t0.250\tClaude", table)
        self.assertEqual([c["why"] for c in chosen], ["сказано дважды"])
        self.assertEqual(len(ctx.notes), 2)

    def test_what_is_cut_already_is_not_in_the_text(self):
        import tempfile

        from runtime.pipelines.editing import plan_editing

        seen = {}

        def answer(key, question, payload):
            seen.update(payload)
            return True, {"items": []}

        with tempfile.TemporaryDirectory() as tmp:
            plan_editing(self.ctx({"editor": True}, answer, tmp), said("Первое второе третье четвёртое."), [{"drop": [0.0, 0.5]}])
            text = open(seen["text"], encoding="utf-8").read()
        self.assertNotIn("Первое", text)

    def test_off_unless_the_profile_asks(self):
        import tempfile

        from runtime.pipelines.editing import plan_editing

        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.ctx({}, lambda *a: self.fail("спрашивать нечего"), tmp)
            self.assertEqual(plan_editing(ctx, said("Текст."), []), [])


class Transcript(unittest.TestCase):
    def test_the_paid_speech_of_the_source_outlives_the_run(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest import mock

        from runtime.pipelines.context import Context
        from runtime.pipelines.words import recognise

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "видео.mp4"
            src.write_bytes(b"0")
            ctx = Context.__new__(Context)
            ctx.src, ctx.outdir, ctx.work = src, Path(tmp) / "выпуск", Path(tmp) / "выпуск" / ".aiediting-run"
            ctx.profile, ctx.info = {"asr": {"provider": "x"}}, {"has_audio": True}
            result = {"words": [{"text": "да", "start": 0.0, "end": 0.2}]}
            with mock.patch("runtime.asr.transcribe", return_value=result) as paid:
                recognise(ctx)
                recognise(ctx)
            self.assertEqual(paid.call_count, 1)
            kept = list((ctx.outdir / ".расшифровка").glob("words-*.json"))
            self.assertEqual(json.loads(kept[0].read_text(encoding="utf-8")), result)


if __name__ == "__main__":
    unittest.main()

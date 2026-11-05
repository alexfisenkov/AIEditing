"""The graphics step hands over the finished video and its words in that video's seconds, with cuts or without."""
import json
import os
import subprocess
import sys
import types
from unittest import mock

from _support import SKILL, TempDirCase, make_av, needs_ffmpeg
from test_pipelines_helpers import LESSON, LESSON_SECONDS, asr_config, bursts, profile

sys.path.insert(0, str(SKILL / "tools"))
sys.path.insert(0, str(SKILL / "templates" / "format-skill"))
from approvals import AutoApprover  # noqa: E402

AE = SKILL / "tools" / "ae.py"


def said(folder):
    rows = (folder / "слова-таймкоды.txt").read_text(encoding="utf-8").splitlines()
    return [(float(r[:7]), r[8:]) for r in rows]


class Words(TempDirCase):
    def run_it(self, steps, answers=None, **params):
        from runtime import pipelines

        video = self.tmp / "запись.mp4"
        if not video.exists():
            make_av(video, [(a, b) for a, b, _ in LESSON], LESSON_SECONDS, size="320x180")
        issue = self.tmp / "выпуск"
        issue.mkdir(exist_ok=True)
        if answers:
            (issue / "ответы.json").write_text(json.dumps(answers), encoding="utf-8")
        report = pipelines.run(video, profile(steps, asr_config(self.tmp, bursts(LESSON)), **params), issue,
                               AutoApprover(issue))
        return video, issue, report

    @needs_ffmpeg
    def test_whole_recording_keeps_the_seconds_and_is_not_stored_twice(self):
        video, issue, report = self.run_it(["write_srt", "graphics"])
        # the fake recogniser tells words by their length only; a hesitation is in neither the .srt nor the words file
        self.assertEqual(len(said(issue)), len(LESSON) - 1)
        self.assertAlmostEqual(said(issue)[2][0], LESSON[3][0], delta=0.05)
        self.assertEqual((issue / "запись.mp4").stat().st_ino, video.stat().st_ino)
        text = (issue / "отчёт.md").read_text(encoding="utf-8")
        self.assertIn("## Решено без вопросов", text)
        self.assertIn("srt: принято", text)
        self.assertIn("Графика ещё не наложена", text)

    @needs_ffmpeg
    def test_a_run_repeated_into_the_same_folder_finds_its_link(self):
        video, issue, _ = self.run_it(["graphics"])
        _, issue, _ = self.run_it(["graphics"])
        self.assertEqual((issue / "запись.mp4").stat().st_ino, video.stat().st_ino)

    @needs_ffmpeg
    def test_another_recording_of_the_same_name_does_not_write_through_the_link(self):
        from runtime import pipelines

        first, issue, _ = self.run_it(["graphics"])
        before = first.read_bytes()
        (self.tmp / "другая").mkdir()
        second = make_av(self.tmp / "другая" / "запись.mp4", [(1.0, 3.0)], 5.0, size="320x180")
        config = asr_config(self.tmp, bursts(LESSON))
        pipelines.run(second, profile(["graphics"], config), issue, AutoApprover(issue))
        self.assertEqual(first.read_bytes(), before)
        self.assertEqual((issue / "запись.mp4").stat().st_ino, second.stat().st_ino)

    @needs_ffmpeg
    def test_a_change_of_picture_after_a_linked_run_leaves_the_source_alone(self):
        video, issue, _ = self.run_it(["graphics"])
        before = video.read_bytes()
        self.run_it(["graphics"], speed=1.25)
        self.assertEqual(video.read_bytes(), before)
        self.assertNotEqual((issue / "запись.mp4").stat().st_ino, video.stat().st_ino)

    @needs_ffmpeg
    def test_a_frame_that_is_not_wide_gets_no_graphics_and_says_so(self):
        from runtime import pipelines

        video = make_av(self.tmp / "вертикаль.mp4", [(a, b) for a, b, _ in LESSON], LESSON_SECONDS, size="120x160")
        issue = self.tmp / "выпуск-в"
        issue.mkdir()
        pipelines.run(video, profile(["write_srt", "graphics"], asr_config(self.tmp, bursts(LESSON))), issue, AutoApprover(issue))
        self.assertFalse((issue / "слова-таймкоды.txt").exists())
        self.assertIn("рассчитана на кадр 16:9", (issue / "отчёт.md").read_text(encoding="utf-8"))

    @needs_ffmpeg
    def test_after_cuts_and_speed_the_seconds_are_the_finished_videos(self):
        _, issue, report = self.run_it(["speech_spans", "cut_spans", "graphics"], answers={"retakes": False}, speed=1.25)
        rows = said(issue)
        self.assertEqual([t for t, _ in rows], sorted(t for t, _ in rows))
        last = next(t for t, w in rows if w == LESSON[-1][2])
        self.assertLess(last, LESSON[-1][0] / 1.25)  # earlier than speed alone: the pauses went too
        self.assertLess(last, report["outputs"][0]["duration"])


class HeardAgain(TempDirCase):
    def ctx(self, provider, keep, speed=1.0, steps=()):
        final = self.tmp / "готово.mp4"
        final.write_bytes(b"x")
        return types.SimpleNamespace(
            profile={"asr": {"provider": provider}}, keep=keep, p=lambda name, d=None: speed if name == "speed" else d,
            report={"outputs": [{"video": final}]}, has=lambda s: s in steps, srt_glossary={},
            transcript=lambda: {"words": [{"start": 10.0, "end": 11.0, "text": "старое", "type": "word"}]})

    def test_a_cut_on_local_whisper_takes_the_words_of_the_finished_video(self):
        from runtime.pipelines import graphics

        heard = {"words": [{"start": 1.0, "end": 2.0, "text": "услышано", "type": "word"},
                           {"start": 5.0, "end": 16.0, "text": "конец", "type": "word"}]}
        with mock.patch("runtime.pipelines.words.recognise", return_value=heard), mock.patch("runtime.media.write_srt") as srt, \
                mock.patch("runtime.media.probe", return_value={"duration": 16.0}):
            words = graphics._finished_words(self.ctx("whispercpp", [(0, 5), (9, 20)], steps=("write_srt",)))
        self.assertEqual([w["text"] for w in words], ["услышано", "конец"])
        self.assertEqual(srt.call_count, 1)

    def test_what_the_second_hearing_lost_comes_from_the_first(self):
        from runtime.pipelines import graphics

        heard = {"words": [{"start": 0.5, "end": 1.0, "text": "начало", "type": "word"},
                           {"start": 14.0, "end": 15.0, "text": "конец", "type": "word"}]}
        with mock.patch("runtime.pipelines.words.recognise", return_value=heard), mock.patch("runtime.media.write_srt"), \
                mock.patch("runtime.media.probe", return_value={"duration": 16.0}):
            words = graphics._finished_words(self.ctx("whispercpp", [(0, 2), (3, 20)]))
        self.assertEqual([w["text"] for w in words], ["начало", "старое", "конец"])

    def test_exact_times_and_a_whole_recording_are_not_heard_twice(self):
        from runtime.pipelines import graphics

        with mock.patch("runtime.pipelines.words.recognise") as recognise:
            graphics._finished_words(self.ctx("scribe", [(0, 5), (9, 20)]))
            graphics._finished_words(self.ctx("whispercpp", [(0, 20)]))
        recognise.assert_not_called()


class Phantoms(TempDirCase):
    def test_film_credits_are_not_speech(self):
        from runtime.asr.whispercpp import drop_phantoms

        words = [{"text": t} for t in ("Субтитры", "создавал", "DimaTorzok", "Нет", "продолжение", "следует...", "своей", "системы")]
        self.assertEqual([w["text"] for w in drop_phantoms(words)], ["Нет", "своей", "системы"])

    def test_the_same_words_apart_stay(self):
        from runtime.asr.whispercpp import drop_phantoms

        words = [{"text": t} for t in ("субтитры", "рядом", "продолжение", "урока")]
        self.assertEqual(len(drop_phantoms(words)), 4)

    def test_a_stretch_with_sound_and_no_words_is_not_reported_as_heard(self):
        from runtime.pipelines.graphics import _lost_words

        (self.tmp / "a.mp4").write_bytes(b"x")
        notes = []
        ctx = types.SimpleNamespace(src=self.tmp / "a.mp4", work=self.tmp / "w", outdir=self.tmp / "o", loud=[(0.0, 60.0)],
                                    info={"duration": 60.0}, profile={"asr": {"provider": "whispercpp"}, "language": "ru"},
                                    note=notes.append)
        with mock.patch("runtime.media.cut_spans", return_value=self.tmp / "к.mp4"), \
                mock.patch("runtime.asr.transcribe", return_value={"words": []}):
            self.assertEqual(_lost_words(ctx, {"words": []}), [])
        self.assertEqual(notes, [])


class Report(TempDirCase):
    def ctx(self, keep=((0.0, 90.0),), pieces=None):
        return types.SimpleNamespace(keep=list(keep), pieces=pieces, info={"duration": 90.0}, src=self.tmp / "a.mp4")

    def test_a_difference_is_the_recordings_only_when_it_measures_the_same(self):
        from runtime.pipelines.report import _from_recording

        with mock.patch("runtime.media.drift_ms", return_value=147.0):
            self.assertTrue(_from_recording(self.ctx(), 147.0))
            self.assertFalse(_from_recording(self.ctx(), 300.0), "the processing added to it")
            self.assertFalse(_from_recording(self.ctx(keep=((0.0, 40.0), (50.0, 90.0))), 147.0), "there are seams")
            self.assertFalse(_from_recording(self.ctx(pieces=[{}]), 147.0))
            self.assertFalse(_from_recording(self.ctx(), 10.0))


class LostWords(TempDirCase):
    def ctx(self, words, loud):
        return types.SimpleNamespace(src=self.tmp / "a.mp4", work=self.tmp / "w", outdir=self.tmp / "o", loud=loud,
                                     info={"duration": 60.0}, profile={"asr": {"provider": "whispercpp"}, "language": "ru"},
                                     note=lambda s: self.notes.append(s))

    def setUp(self):
        super().setUp()
        self.notes = []

    def test_a_real_pause_is_left_and_a_lost_stretch_is_heard_again(self):
        from runtime.pipelines.graphics import _lost_words

        said_words = {"words": [{"start": 1.0, "end": 2.0, "text": "раз", "type": "word"},
                                {"start": 20.0, "end": 21.0, "text": "два", "type": "word"},
                                {"start": 40.0, "end": 41.0, "text": "три", "type": "word"}]}
        loud = [(1.0, 2.0), (20.0, 40.0)]  # silence up to the second word, sound after it
        heard = {"words": [{"start": 10.0, "end": 10.5, "text": "контекст", "type": "word"},
                           {"start": 18.0, "end": 18.5, "text": "потерянное", "type": "word"}]}
        (self.tmp / "a.mp4").write_bytes(b"x")
        with mock.patch("runtime.media.cut_spans", return_value=self.tmp / "кусок.mp4") as cut, \
                mock.patch("runtime.asr.transcribe", return_value=heard):
            found = _lost_words(self.ctx(said_words, loud), said_words)
        self.assertEqual(cut.call_count, 1)
        self.assertEqual(cut.call_args[0][1], [(9.0, 52.0)])
        self.assertEqual([(round(w["start"], 1), w["text"]) for w in found], [(27.0, "потерянное")])
        self.assertEqual(len(list((self.tmp / "o" / ".расшифровка").glob("дочитано-*.json"))), 1)
        self.assertEqual(len(self.notes), 1)

    def test_a_run_coming_back_after_a_question_does_not_listen_twice(self):
        from runtime.pipelines.graphics import _lost_words
        from runtime.pipelines.words import cache_key

        (self.tmp / "a.mp4").write_bytes(b"x")
        ctx = self.ctx({"words": []}, [])
        kept = self.tmp / "o" / ".расшифровка"
        kept.mkdir(parents=True)
        (kept / "дочитано-{}.json".format(cache_key(ctx.src, ctx.profile["asr"]))).write_text(
            '[{"start": 5.0, "end": 6.0, "text": "уже", "type": "word"}]', encoding="utf-8")
        with mock.patch("runtime.asr.transcribe") as transcribe:
            found = _lost_words(ctx, {"words": []})
        transcribe.assert_not_called()
        self.assertEqual(found[0]["text"], "уже")
        self.assertEqual(len(self.notes), 1)

    def test_what_was_heard_for_one_recording_does_not_join_another(self):
        from runtime.pipelines.graphics import _lost_words

        (self.tmp / "a.mp4").write_bytes(b"x")
        kept = self.tmp / "o" / ".расшифровка"
        kept.mkdir(parents=True)
        (kept / "дочитано-другая.json").write_text('[{"start": 5.0, "end": 6.0, "text": "чужое", "type": "word"}]', encoding="utf-8")
        ctx = self.ctx({"words": []}, [])
        ctx.loud = []
        self.assertEqual(_lost_words(ctx, {"words": []}), [])


class Build(TempDirCase):
    def build(self, steps, approval="plan"):
        draft = self.tmp / "work" / "монтаж-проба"
        draft.mkdir(parents=True)
        (draft / "profile.json").write_text(json.dumps(dict(
            profile(steps, {"provider": "command", "language": "ru", "model": None, "base_url": None,
                            "api_key_env": None, "command": ["нет"]}),
            approval=approval, design="design/", taste=[])), encoding="utf-8")
        done = subprocess.run([sys.executable, str(AE), "build-skill", str(draft / "profile.json"), str(self.tmp / "out")],
                              capture_output=True, text=True, encoding="utf-8",
                              env=dict(os.environ, AIEDITING_WORK=str(self.tmp / "work")))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return self.tmp / "out" / "монтаж-проба"

    def test_a_graphics_format_carries_the_kit_and_its_method(self):
        skill = self.build(["write_srt", "graphics"], approval="auto")
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue((skill / "design" / "overlay-kit" / "README.md").is_file())
        self.assertIn("## Graphics", text)
        self.assertIn("## Without questions", text)
        self.assertIn("«Без вопросов»", text)
        self.assertNotIn("The editor's pass", text)
        self.assertNotIn("{{", text)
        self.assertIn("and what «Graphics» names", text)
        self.assertFalse((skill / "design" / "overlay-kit" / "template" / "node_modules").exists())

    def test_a_format_without_a_design_gets_the_example_and_the_kit_is_renewed(self):
        from aelib import assemble

        design = self.tmp / "design"
        (design / "overlay-kit").mkdir(parents=True)
        (design / "overlay-kit" / assemble.KIT_MARK).write_text("x", encoding="utf-8")
        (design / "overlay-kit" / "старое.txt").write_text("x", encoding="utf-8")
        assemble._graphics_parts(design)
        self.assertFalse((design / "overlay-kit" / "старое.txt").exists())
        self.assertTrue((design / "overlay-kit" / "README.md").is_file())
        self.assertTrue((design / "tokens.json").is_file())

    def test_a_kit_the_format_made_its_own_stays(self):
        from aelib import assemble

        design = self.tmp / "design"
        (design / "overlay-kit").mkdir(parents=True)
        (design / "overlay-kit" / "своё.txt").write_text("x", encoding="utf-8")
        (design / "tokens.json").write_text("{}", encoding="utf-8")
        assemble._graphics_parts(design)
        self.assertTrue((design / "overlay-kit" / "своё.txt").is_file())
        self.assertEqual((design / "tokens.json").read_text(encoding="utf-8"), "{}")

    def test_a_cutting_format_is_as_it_was_and_knows_the_mode(self):
        skill = self.build(["speech_spans", "cut_spans"])
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("The editor's pass", text)
        self.assertIn("## Without questions", text)
        self.assertNotIn("## Graphics", text)
        self.assertFalse((skill / "design" / "overlay-kit").exists())

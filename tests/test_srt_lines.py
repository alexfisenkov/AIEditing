import unittest

import _support  # noqa: F401  (puts the skill on sys.path)


def tokens(text, step=0.3, gap_after=None):
    """Words of `text`, one every `step` s; gap_after={i: seconds} adds a pause after word i."""
    out, t = [], 0.0
    for i, w in enumerate(text.split()):
        out.append({"text": w, "start": round(t, 3), "end": round(t + step * 0.8, 3)})
        t += step + (gap_after or {}).get(i, 0.0)
    return out


def texts(cues):
    return [c["text"] for c in cues]


class Breaks(unittest.TestCase):
    def cut(self, text, glossary=None, **kw):
        from runtime.media.srt_lines import lines

        return lines(tokens(text, **kw), glossary)

    def test_a_latin_name_is_never_split(self):
        cues = texts(self.cut("И как только отдадим его уже в Claude Code, Claude Code уже сможет нам, соответственно..."))
        for a, b in zip(cues, cues[1:]):
            self.assertFalse(a.endswith("Claude") and b.startswith("Code"), cues)
        self.assertTrue(all(len(c) > len("соответственно...") for c in cues), cues)

    def test_a_glossary_phrase_is_kept_whole_before_it_is_replaced(self):
        text = "переустановить-обязательно-полностью клод код сегодня же"
        self.assertIn("клод", texts(self.cut(text))[0])  # without the glossary it would split «клод | код»
        cues = texts(self.cut(text, {"клод код": "Клод Код"}))  # same length: only the glue keeps it whole
        self.assertTrue(any("клод код" in c for c in cues), cues)

    def test_a_line_is_measured_after_the_glossary(self):
        from runtime.media.srt_lines import MAX_CHARS, glosser

        glossary = {"клод код": "Claude Code", "гпт": "ChatGPT Plus"}
        cues = self.cut("ставим клод код и гпт, потом клод код и гпт, и ещё раз клод код.", glossary)
        for c in texts(cues):
            self.assertLessEqual(len(glosser(glossary)(c)), MAX_CHARS, cues)

    def test_no_cue_ends_on_a_preposition(self):
        from runtime.media.srt_words import CLINGS, bare

        for text in ("потому что именно в этом приложении мы сможем тогда с вами создать свою собственную "
                     "дизайн-систему.", "Обязательно сохраните файл перед запуском этой длинной команды.",
                     "Сначала проверьте настройки после установки новой версии программы."):
            cues = texts(self.cut(text))
            for c in cues[:-1]:
                self.assertNotIn(bare(c.split()[-1]), CLINGS, cues)

    def test_a_compound_conjunction_stays_whole(self):
        for text, pair in (("Это нужно потому что иначе ничего не заработает.", "потому что"),
                           ("Мы сделали это для того чтобы ученики не путались в папках.", "для того чтобы")):
            cues = texts(self.cut(text))
            self.assertTrue(any(pair in c for c in cues), cues)

    def test_a_version_stays_with_its_name(self):
        for text, name in (("Мы переключаемся на Claude Opus 4.5 прямо в настройках проекта.", "Claude Opus 4.5"),
                           ("Дальше мы подключаем Gemini 2.5 Pro прямо внутри редактора кода.", "Gemini 2.5 Pro"),
                           ("Сегодня проверим всё это на новом iPhone 17 Pro прямо у меня в руках.", "iPhone 17 Pro")):
            cues = texts(self.cut(text))
            self.assertTrue(any(name in c for c in cues), cues)

    def test_ok_ends_a_sentence(self):
        cues = texts(self.cut("Всё ок. Теперь открываем терминал и вводим команду."))
        self.assertEqual(cues[0], "Всё ок.")

    def test_a_comma_is_where_it_breaks(self):
        cues = texts(self.cut("И для того чтобы создать ИИ-дизайнера, самый первый шаг, который нужно сделать,"
                              " это открыть приложение Claude Desktop."))
        self.assertTrue(all(c.endswith((",", ".")) for c in cues), cues)

    def test_limits_order_and_every_word_kept(self):
        from runtime.media.srt_lines import MAX_CHARS, MAX_SECONDS

        text = ("Уже после дизайн-системы мы с вами будем отдавать её непосредственно на реализацию в ваш "
                "Claude. И как только отдадим его уже в Claude Code, Claude Code уже сможет нам помочь.")
        cues = self.cut(text, gap_after={14: 1.2})
        self.assertEqual(" ".join(texts(cues)), text)
        end = 0.0
        for c in cues:
            self.assertLessEqual(len(c["text"]), MAX_CHARS)
            self.assertLessEqual(c["end"] - c["start"], MAX_SECONDS)
            self.assertLessEqual(end, c["start"])
            end = c["end"]

    def test_a_pause_and_a_sentence_end_always_break(self):
        cues = texts(self.cut("Первое. второе третье", gap_after={1: 1.5}))
        self.assertEqual(cues, ["Первое.", "второе", "третье"])

    def test_a_name_longer_than_a_line_is_still_cut(self):
        cues = texts(self.cut("Open Router Claude Code Claude Desktop Google Drive Figma Make Hyper Frames"))
        self.assertGreater(len(cues), 1)
        self.assertEqual(" ".join(cues).split(), "Open Router Claude Code Claude Desktop Google Drive Figma "
                                                 "Make Hyper Frames".split())


class Sentences(unittest.TestCase):
    def capitals(self, words):
        from runtime.media.srt import _tokens

        return [t["text"] for t in _tokens([{"text": w, "start": i, "end": i + 0.5, "type": "word"}
                                            for i, w in enumerate(words)])]

    def test_a_sentence_starts_with_a_capital_letter(self):
        self.assertEqual(self.capitals(["работает", ".", "давайте", "вот", "."]), ["Работает.", "Давайте", "вот."])

    def test_a_brand_keeps_its_own_case(self):
        self.assertEqual(self.capitals(["настройки.", "iCloud", "синхронизирует.", "macOS", "спросит.", "n8n"]),
                         ["Настройки.", "iCloud", "синхронизирует.", "macOS", "спросит.", "n8n"])

    def test_no_capital_after_an_ellipsis_or_an_abbreviation(self):
        self.assertEqual(self.capitals(["ну", "вот...", "и", "тогда", "т.е.", "так"]),
                         ["Ну", "вот...", "и", "тогда", "т.е.", "так"])


if __name__ == "__main__":
    unittest.main()

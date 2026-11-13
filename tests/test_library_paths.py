"""The library: one pointer per computer, a fixed layout, the env variable wins over the pointer."""
import json
import os
import unittest
from unittest import mock

from _support import TempDirCase


class LibraryCase(TempDirCase):
    """A home of its own: the pointer and the config folder never touch the real one."""

    def setUp(self):
        super().setUp()
        home = self.tmp / "дом"
        home.mkdir()
        env = {"HOME": str(home), "USERPROFILE": str(home), "LOCALAPPDATA": str(home / "AppData")}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("AIEDITING_LIBRARY", None)
        self.home = home


class Pointer(LibraryCase):
    def test_nothing_is_found_before_a_library_is_chosen(self):
        from runtime.library.paths import find_library

        self.assertIsNone(find_library())

    def test_the_pointer_lives_in_the_aiediting_config_folder(self):
        from runtime.library.paths import pointer_file

        if os.name == "nt":
            self.assertEqual(pointer_file(), self.home / "AppData" / "AIEditing" / "library.json")
        else:
            self.assertEqual(pointer_file(), self.home / ".aiediting" / "library.json")

    def test_set_writes_the_layout_and_the_pointer_and_any_skill_finds_it(self):
        from runtime.library.paths import LAYOUT, find_library, pointer_file, set_library

        lib = set_library(self.tmp / "Моя библиотека")
        self.assertEqual(find_library(), lib)
        self.assertEqual(json.loads(pointer_file().read_text(encoding="utf-8"))["path"], str(lib))
        for rel in ("обо-мне/кто-я.md", "обо-мне/путь-жизни.md", "обо-мне/люди.md", "обо-мне/места.md",
                    "обо-мне/хобби.md", "обо-мне/блог.md", "правила.md", "чего-нельзя.md", "README.md",
                    "опись/галерея.jsonl", "опись/instagram.jsonl", "опись/футажи.jsonl", "опись/стоки.jsonl",
                    "опись/прогресс.json"):
            self.assertTrue((lib / rel).is_file(), rel)
        for rel in ("обо-мне/документы", "футажи", "фото", "instagram", "стоки", "музыка", "звуки"):
            self.assertTrue((lib / rel).is_dir(), rel)
        for rel in LAYOUT.values():
            self.assertTrue((lib / rel).exists(), rel)
        self.assertIn("год — событие — место", (lib / "обо-мне" / "путь-жизни.md").read_text(encoding="utf-8"))

    def test_set_again_keeps_what_the_person_wrote(self):
        from runtime.library.paths import set_library

        lib = set_library(self.tmp / "биб")
        (lib / "обо-мне" / "кто-я.md").write_text("# Кто я\n\nРыбак из Твери\n", encoding="utf-8")
        set_library(lib)
        self.assertIn("Рыбак из Твери", (lib / "обо-мне" / "кто-я.md").read_text(encoding="utf-8"))

    def test_the_env_variable_overrides_the_pointer(self):
        from runtime.library.paths import find_library, set_library

        set_library(self.tmp / "по указателю")
        other = self.tmp / "из переменной"
        other.mkdir()
        with mock.patch.dict(os.environ, {"AIEDITING_LIBRARY": str(other)}):
            self.assertEqual(find_library(), other.resolve())

    def test_a_pointer_to_a_missing_folder_finds_nothing(self):
        import shutil

        from runtime.library.paths import find_library, set_library

        lib = set_library(self.tmp / "на диске")
        shutil.rmtree(str(lib))
        self.assertIsNone(find_library())


if __name__ == "__main__":
    unittest.main()

"""Recipe helpers publish new artifacts without altering source files."""
import json
import os
import errno
import sys
from pathlib import Path
from unittest import mock

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))


class RecipeOutputs(TempDirCase):
    def test_volume_without_hardlinks_uses_exclusive_copy(self):
        from recipe_lib.common import output_file
        for number in (errno.ENOTSUP, errno.EPERM, errno.EINVAL, errno.ENOSYS):
            with self.subTest(errno=number):
                out = self.tmp / ("external-{}.mp4".format(number))
                with mock.patch("recipe_lib.common.os.link", side_effect=OSError(number, "no hard links")):
                    with output_file(out) as staged:
                        staged.write_bytes(b"finished")
                self.assertEqual(out.read_bytes(), b"finished")
                with self.assertRaises(FileExistsError):
                    with output_file(out) as staged:
                        staged.write_bytes(b"replace")
                self.assertEqual(out.read_bytes(), b"finished")

    def test_failed_exclusive_copy_removes_its_partial_output(self):
        from recipe_lib.common import output_file
        out = self.tmp / "failed.mp4"
        def fail_copy(source, destination, **kwargs):
            destination.write(b"partial")
            raise OSError("disk full")
        with mock.patch("recipe_lib.common.os.link", side_effect=OSError(errno.ENOTSUP, "no hard links")), \
                mock.patch("recipe_lib.common.shutil.copyfileobj", fail_copy):
            with self.assertRaises(OSError):
                with output_file(out) as staged:
                    staged.write_bytes(b"complete")
        self.assertFalse(out.exists())

    def test_json_is_written_once_unless_replace_is_explicit(self):
        from recipe_lib.common import write_json
        out = self.tmp / "результат с пробелом.json"
        write_json(out, {"value": 1})
        with self.assertRaises(FileExistsError):
            write_json(out, {"value": 2})
        self.assertEqual(json.loads(out.read_text()), {"value": 1})
        write_json(out, {"value": 3}, replace=True)
        self.assertEqual(json.loads(out.read_text()), {"value": 3})

    def test_failure_never_replaces_previous_output(self):
        from recipe_lib.common import output_file
        out = self.tmp / "out.mp4"
        out.write_bytes(b"previous")
        with self.assertRaises(RuntimeError):
            with output_file(out, replace=True) as staged:
                staged.write_bytes(b"partial")
                raise RuntimeError("failed")
        self.assertEqual(out.read_bytes(), b"previous")

    def test_source_and_hardlink_alias_are_protected(self):
        from recipe_lib.common import output_file, RecipeError
        src, alias = self.tmp / "source.mp4", self.tmp / "alias.mp4"
        src.write_bytes(b"original")
        os.link(src, alias)
        for out in (src, alias):
            with self.assertRaises(RecipeError):
                with output_file(out, replace=True, sources=[src]) as staged:
                    staged.write_bytes(b"changed")
        self.assertEqual(src.read_bytes(), b"original")

    def test_empty_output_is_not_published(self):
        from recipe_lib.common import output_file, RecipeError
        out = self.tmp / "empty.mp4"
        with self.assertRaises(RecipeError):
            with output_file(out) as staged:
                staged.touch()
        self.assertFalse(out.exists())

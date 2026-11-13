"""The inventory: code measures new files, the agent describes them in batches, nothing is described twice."""
import json
import unittest

from _support import ffmpeg, needs_ffmpeg
from test_library_paths import LibraryCase

try:
    from PIL import Image
except ImportError:  # Pillow is optional; the photo tests need it to write EXIF
    Image = None

needs_pillow = unittest.skipUnless(Image is not None, "Pillow is not installed")


def video(path, size="320x180", seconds=2, created=None, rotation=None):
    args = ["-f", "lavfi", "-i", "testsrc=s={}:r=25:d={}".format(size, seconds)]
    if created:
        args += ["-metadata", "creation_time={}".format(created)]
    args += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(path)]
    if rotation is None:
        ffmpeg(*args)
        return path
    coded = path.with_name("coded-" + path.name)
    ffmpeg(*args[:-1], str(coded))
    ffmpeg("-display_rotation", str(rotation), "-i", str(coded), "-c", "copy", str(path))
    coded.unlink()
    return path


def photo(path, size=(200, 100), taken=None, orientation=None):
    exif = Image.Exif()
    if taken:
        exif[306] = taken
    if orientation:
        exif[274] = orientation
    Image.new("RGB", size, (90, 140, 200)).save(str(path), exif=exif)
    return path


class Inventory(LibraryCase):
    def setUp(self):
        super().setUp()
        from runtime.library.paths import set_library

        self.lib = set_library(self.tmp / "библиотека")
        self.src = self.tmp / "Галерея с телефона"
        self.src.mkdir()

    @needs_ffmpeg
    def test_scan_measures_date_orientation_with_rotation_and_length(self):
        from runtime.library import inventory

        video(self.src / "море.mp4", created="2019-07-14T10:00:00.000000Z")
        video(self.src / "телефон.mp4", rotation=90)
        (self.src / "заметка.txt").write_text("не медиа", encoding="utf-8")
        rows = {r["f"].rsplit("/", 1)[-1]: r for r in inventory.scan(self.lib, "галерея", [self.src])}
        self.assertEqual(sorted(rows), ["море.mp4", "телефон.mp4"])
        sea, phone = rows["море.mp4"], rows["телефон.mp4"]
        self.assertEqual(sea["date"], "2019-07-14")
        self.assertEqual((sea["type"], sea["orient"]), ("видео", "гор"))
        self.assertEqual(phone["orient"], "верт")
        self.assertAlmostEqual(sea["dur"], 2.0, delta=0.2)
        self.assertEqual(sea["kind"], "галерея")
        self.assertEqual(sea["what"], "")

    @needs_ffmpeg
    @needs_pillow
    def test_a_photo_takes_its_date_and_turn_from_exif(self):
        from runtime.library import inventory

        photo(self.src / "лежит.jpg", taken="2021:06:01 12:00:00", orientation=6)
        photo(self.src / "квадрат.png", size=(120, 120))
        rows = {r["f"].rsplit("/", 1)[-1]: r for r in inventory.scan(self.lib, "галерея", [self.src])}
        self.assertEqual(rows["лежит.jpg"]["date"], "2021-06-01")
        self.assertEqual((rows["лежит.jpg"]["type"], rows["лежит.jpg"]["orient"]), ("фото", "верт"))
        self.assertIsNone(rows["лежит.jpg"]["dur"])
        self.assertEqual(rows["квадрат.png"]["orient"], "кв")
        self.assertIsNone(rows["квадрат.png"]["date"])

    @needs_ffmpeg
    def test_described_files_are_not_returned_again_and_progress_is_kept(self):
        from runtime.library import inventory

        video(self.src / "a.mp4")
        video(self.src / "b.mp4")
        first = inventory.scan(self.lib, "галерея", [self.src])
        self.assertEqual(len(first), 2)
        self.assertEqual(len(inventory.pending(self.lib, "галерея")), 2)
        done = inventory.describe(self.lib, "галерея", [{"f": first[0]["f"], "what": "закат", "who": ["Петя"],
                                                          "phrases": ["вечер у моря"]}])
        self.assertEqual(done, 1)
        self.assertEqual([r["f"] for r in inventory.pending(self.lib, "галерея")], [first[1]["f"]])
        again = inventory.scan(self.lib, "галерея", [])  # the folder remembered by the first scan
        self.assertEqual([r["f"] for r in again], [first[1]["f"]])
        saved = inventory.load(self.lib)
        self.assertEqual(len(saved), 1)
        self.assertEqual((saved[0]["what"], saved[0]["who"], saved[0]["orient"]), ("закат", ["Петя"], "гор"))
        progress = json.loads((self.lib / "опись" / "прогресс.json").read_text(encoding="utf-8"))
        self.assertEqual(progress["kinds"]["галерея"]["described"], 1)
        inventory.describe(self.lib, "галерея", [{"f": first[0]["f"], "what": "закат над морем"}])
        self.assertEqual([r["what"] for r in inventory.load(self.lib, ["галерея"])], ["закат над морем"])

    def test_an_unknown_kind_is_refused_in_russian(self):
        from runtime.library import inventory
        from runtime.library.paths import LibraryError

        with self.assertRaises(LibraryError) as caught:
            inventory.scan(self.lib, "открытки", [self.src])
        self.assertIn("галерея", str(caught.exception))

    def test_a_row_without_a_file_is_refused(self):
        from runtime.library import inventory
        from runtime.library.paths import LibraryError

        with self.assertRaises(LibraryError):
            inventory.describe(self.lib, "галерея", [{"what": "без файла"}])

    @needs_ffmpeg
    def test_sheet_numbers_small_frames_in_a_grid(self):
        from runtime.library import inventory

        files = [video(self.src / "{}.mp4".format(i)) for i in range(3)]
        out = inventory.sheet(files, self.tmp / "лист.jpg", grid=2)
        self.assertTrue(out.is_file())
        if Image is not None:
            with Image.open(str(out)) as im:
                width, height = im.size
            self.assertGreater(width, 0)
            self.assertAlmostEqual(width / height, 1.0, delta=0.15)  # 2 columns × 2 rows of square cells


if __name__ == "__main__":
    unittest.main()

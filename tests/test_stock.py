"""Free stock video by the person's own key: search, cache, download into the library (no network: a local server)."""
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import _support  # noqa: F401  (puts the skill on sys.path)
from _support import TempDirCase
from runtime.library import cli, inventory, paths, stock

SECRET = "sk-test-0123456789"
CLIP = b"not really a video, but a file of bytes"


def pexels_reply(base):
    return {"videos": [
        {"id": 111, "url": "https://example.test/video/111/", "duration": 9, "video_files": [
            {"file_type": "video/mp4", "width": 640, "height": 360, "link": base + "/files/small.mp4"},
            {"file_type": "video/mp4", "width": 1920, "height": 1080, "link": base + "/files/big.mp4"},
            {"file_type": "video/mp4", "width": 1080, "height": 1920, "link": base + "/files/tall.mp4"}]},
        {"id": 222, "url": "https://example.test/video/222/", "duration": 4, "video_files": [
            {"file_type": "video/mp4", "width": 1080, "height": 1920, "link": base + "/files/only-tall.mp4"}]}]}


def pixabay_reply(base):
    return {"hits": [
        {"id": 7, "pageURL": "https://example.test/v/7/", "duration": 12, "videos": {
            "large": {"url": base + "/files/large.mp4", "width": 1920, "height": 1080},
            "medium": {"url": base + "/files/medium.mp4", "width": 1280, "height": 720},
            "small": {"url": "", "width": 0, "height": 0}}},
        {"id": 8, "pageURL": "https://example.test/v/8/", "duration": 5, "videos": {
            "large": {"url": base + "/files/tall.mp4", "width": 1080, "height": 1920}}}]}


class StockApi:
    """Plays the two services and a file server on 127.0.0.1; `status` makes every answer an error."""

    def __init__(self, status=200):
        self.status, self.requests = status, []
        api = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                api.requests.append({"path": self.path, "headers": self.headers})
                base = api.url
                if api.status != 200:
                    body, code = b'{"error": "no"}', api.status
                elif self.path.startswith("/pexels"):
                    body, code = json.dumps(pexels_reply(base)).encode(), 200
                elif self.path.startswith("/pixabay"):
                    body, code = json.dumps(pixabay_reply(base)).encode(), 200
                else:
                    body, code = CLIP, 200
                self.send_response(code)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:{}".format(self.server.server_address[1])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()

    def urls(self):
        return {"pexels": self.url + "/pexels", "pixabay": self.url + "/pixabay"}


class StockCase(TempDirCase):
    def setUp(self):
        super().setUp()
        self.lib = paths.make_layout(self.tmp / "библиотека")
        env = mock.patch.dict(os.environ, {"AIEDITING_LIBRARY": str(self.lib), "PEXELS_API_KEY": SECRET,
                                           "PIXABAY_API_KEY": SECRET})
        env.start()
        self.addCleanup(env.stop)


class Search(StockCase):
    def test_pexels_hits_carry_the_best_landscape_file_and_the_key_goes_in_the_header(self):
        with StockApi() as api, mock.patch.dict(stock.URLS, api.urls()):
            hits = stock.search("море на закате", "pexels", per_page=4)
            request = api.requests[0]
        self.assertEqual([h["id"] for h in hits], ["111"])  # 222 only has a tall file
        first = hits[0]
        self.assertEqual((first["provider"], first["width"], first["height"], first["dur"]),
                         ("pexels", 1920, 1080, 9.0))
        self.assertTrue(first["link"].endswith("/files/big.mp4"))
        self.assertEqual(request["headers"]["Authorization"], SECRET)
        self.assertIn("orientation=landscape", request["path"])
        self.assertIn("per_page=4", request["path"])
        self.assertIn("query=", request["path"])

    def test_pixabay_has_no_orientation_so_tall_clips_are_filtered_by_size(self):
        with StockApi() as api, mock.patch.dict(stock.URLS, api.urls()):
            hits = stock.search("город", "pixabay")
        self.assertEqual([h["id"] for h in hits], ["7"])
        self.assertTrue(hits[0]["link"].endswith("/files/large.mp4"))
        self.assertEqual(hits[0]["dur"], 12.0)

    def test_the_same_query_is_asked_once(self):
        with StockApi() as api, mock.patch.dict(stock.URLS, api.urls()):
            first = stock.search("лес", "pexels")
            again = stock.search("лес", "pexels")
        self.assertEqual(first, again)
        self.assertEqual(len(api.requests), 1)

    def test_without_a_key_the_phrase_names_the_variable_and_nothing_is_asked(self):
        env = {k: v for k, v in os.environ.items() if k != "PEXELS_API_KEY"}
        with StockApi() as api, mock.patch.dict(stock.URLS, api.urls()), \
                mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("runtime.asr.secrets._env_files", return_value=[]):
            with self.assertRaises(stock.StockError) as caught:
                stock.search("лес", "pexels")
        self.assertIn("PEXELS_API_KEY", str(caught.exception))
        self.assertEqual(api.requests, [])

    def test_a_refusal_names_the_status_and_never_the_key(self):
        for provider in ("pexels", "pixabay"):
            with StockApi(status=401) as api, mock.patch.dict(stock.URLS, api.urls()):
                with self.assertRaises(stock.StockError) as caught:
                    stock.search("река", provider)
            self.assertIn("401", str(caught.exception))
            self.assertNotIn(SECRET, str(caught.exception))

    def test_an_unknown_provider_is_refused(self):
        with self.assertRaises(stock.StockError):
            stock.search("лес", "somewhere")


class Download(StockCase):
    def hit(self, api):
        with mock.patch.dict(stock.URLS, api.urls()):
            return stock.search("лес", "pexels")[0]

    def test_the_file_lands_in_the_stock_folder_with_a_row_and_the_source(self):
        with StockApi() as api:
            hit = self.hit(api)
            row = stock.download(hit, self.lib)
        file = inventory.file_of(self.lib, row)
        self.assertEqual(file.read_bytes(), CLIP)
        self.assertEqual(file.parent, self.lib / "стоки")
        saved = inventory.load(self.lib, ["стоки"])
        self.assertEqual([r["f"] for r in saved], [row["f"]])
        self.assertEqual((saved[0]["kind"], saved[0]["type"], saved[0]["orient"], saved[0]["dur"]),
                         ("стоки", "видео", "гор", 9.0))
        self.assertIn("pexels", saved[0]["source"])
        self.assertIn("111", saved[0]["source"])
        self.assertIn("лес", saved[0]["what"])
        self.assertNotIn("pexels", row["f"])  # nothing of the service in the file name the person sees

    def test_the_same_hit_is_not_fetched_or_written_twice(self):
        with StockApi() as api:
            hit = self.hit(api)
            first = stock.download(hit, self.lib)
            before = len(api.requests)
            second = stock.download(hit, self.lib)
        self.assertEqual(first["f"], second["f"])
        self.assertEqual(len(api.requests), before)
        self.assertEqual(len(inventory.load(self.lib, ["стоки"])), 1)

    def test_a_hit_without_a_link_is_refused(self):
        with self.assertRaises(stock.StockError):
            stock.download({"provider": "pexels", "id": "1"}, self.lib)


class Moved:
    """A server on 127.0.0.1 that answers every request 302 to `target` + the same path."""

    def __init__(self, target):
        moved = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", moved.target + self.path)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args):
                pass

        self.target = target
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:{}".format(self.server.server_address[1])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


class Redirect(StockCase):
    def test_a_redirect_to_another_host_never_carries_the_key(self):
        with StockApi() as other:
            elsewhere = other.url.replace("127.0.0.1", "localhost")  # another host name than the one asked
            with Moved(elsewhere) as moved, mock.patch.dict(stock.URLS, {"pexels": moved.url + "/pexels"}):
                hits = stock.search("горы", "pexels")
        self.assertEqual([h["id"] for h in hits], ["111"])
        self.assertEqual(len(other.requests), 1)
        self.assertNotIn("Authorization", other.requests[0]["headers"])

    def test_the_file_goes_to_disk_through_the_services_download_and_a_big_one_is_refused(self):
        from runtime.services import web

        with StockApi() as api:
            hit = self.hit_of(api)
            with mock.patch.object(web, "download", wraps=web.download) as spy:
                stock.download(hit, self.lib)
            self.assertEqual(spy.call_count, 1)
            big = dict(hit, id="другой")
            with mock.patch.object(stock, "MAX_BYTES", len(CLIP) - 1):
                with self.assertRaises(stock.StockError):
                    stock.download(big, self.lib)
        self.assertEqual(len(list((self.lib / "стоки").iterdir())), 1, "no half file is left")

    def hit_of(self, api):
        with mock.patch.dict(stock.URLS, api.urls()):
            return stock.search("лес", "pexels")[0]


class Command(StockCase):
    def test_stock_command_lists_hits_without_links_and_takes_one(self):
        with StockApi() as api, mock.patch.dict(stock.URLS, api.urls()):
            listing = cli.run(["stock", "лес", "--provider", "pexels"])
            taken = cli.run(["stock", "лес", "--provider", "pexels", "--take", "1"])
        self.assertIn("1920", listing)
        self.assertNotIn("http", listing)
        self.assertNotIn(SECRET, listing + taken)
        self.assertEqual(len(inventory.load(self.lib, ["стоки"])), 1)
        self.assertIn("стоки/", taken)


if __name__ == "__main__":
    unittest.main()

"""Auphonic by the person's own key: send, wait, download; the key never shows. No network: a server on 127.0.0.1."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from _fake_http import form_field
from _support import TempDirCase
from runtime.services import auphonic

SECRET = "auph-test-0123456789abcdef"
RESULT = b"RIFF....WAVEfmt cleaned voice"


class AuphonicApi:
    """Plays the simple API, the production status (busy once, then `final`), the download and the account."""

    def __init__(self, status=200, final=3, error=""):
        self.status, self.final, self.error, self.requests, self.polls = status, final, error, [], 0
        api = self

        class Handler(BaseHTTPRequestHandler):
            def _reply(self, code, body, ctype="application/json"):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _json(self, data):
                code = api.status
                if code != 200:  # an unhappy service echoes what it got, the key included
                    data = {"error_message": "bad key " + str(self.headers.get("Authorization"))}
                self._reply(code, json.dumps(data).encode())

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                api.requests.append({"method": "POST", "path": self.path, "headers": self.headers, "body": body})
                self._json({"status_code": 200, "data": {"uuid": "abc123", "status": 9}})

            def do_GET(self):
                api.requests.append({"method": "GET", "path": self.path, "headers": self.headers})
                if self.path == "/api/production/abc123.json":
                    api.polls += 1
                    status = 4 if api.polls == 1 else api.final
                    files = [{"format": "mp3", "ending": "mp3", "download_url": api.url + "/api/download/x/out.mp3"},
                             {"format": "wav", "ending": "wav", "download_url": api.url + "/api/download/x/out.wav"}]
                    self._json({"data": {"uuid": "abc123", "status": status, "status_string": "Error" if status == 2 else "Done",
                                         "error_message": api.error, "output_files": files if status == 3 else []}})
                elif self.path.startswith("/api/download/"):
                    self._reply(200, RESULT if self.path.endswith(".wav") else b"mp3", "audio/wav")
                elif self.path == "/api/user.json":
                    self._json({"data": {"username": "someone", "credits": 1.5}})
                else:
                    self._reply(404, b"{}")

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


class Case(TempDirCase):
    def setUp(self):
        super().setUp()
        self.audio = self.tmp / "голос.wav"
        self.audio.write_bytes(b"RIFF....WAVEfmt original voice")
        for patch in (mock.patch.object(auphonic, "POLL", 0), mock.patch("runtime.asr.secrets._env_files", return_value=[])):
            patch.start()
            self.addCleanup(patch.stop)

    def keyed(self, api):
        return [mock.patch.object(auphonic, "BASE", api.url), mock.patch.dict(os.environ, {"AUPHONIC_API_KEY": SECRET})]

    def run_with(self, api, fn):
        patches = self.keyed(api)
        for p in patches:
            p.start()
        try:
            return fn()
        finally:
            for p in reversed(patches):
                p.stop()


class Process(Case):
    def test_sends_with_the_algorithms_waits_and_downloads_the_wav(self):
        preset = {"denoise": True, "denoisemethod": "dynamic", "denoiseamount": 12, "leveler": True,
                  "normloudness": True, "loudnesstarget": -16}
        with AuphonicApi() as api:
            out = self.run_with(api, lambda: auphonic.process(self.audio, preset, self.tmp / "out" / "чистый.wav"))
        self.assertEqual(out.read_bytes(), RESULT)
        post = api.requests[0]
        self.assertEqual(post["path"], "/api/simple/productions.json")
        self.assertEqual(post["headers"]["Authorization"], "bearer " + SECRET)
        self.assertEqual(form_field(post["body"], "action"), "start")
        self.assertEqual(form_field(post["body"], "denoise"), "true")
        self.assertEqual(form_field(post["body"], "denoisemethod"), "dynamic")
        self.assertEqual(form_field(post["body"], "loudnesstarget"), "-16")
        self.assertIsNone(form_field(post["body"], "preset"))
        self.assertIn(b'name="input_file"; filename="', post["body"])
        self.assertEqual(api.polls, 2)
        self.assertTrue(all(r["headers"]["Authorization"] == "bearer " + SECRET for r in api.requests))

    def test_a_preset_by_name_or_id_is_sent_as_the_preset(self):
        with AuphonicApi() as api:
            self.run_with(api, lambda: auphonic.process(self.audio, "my-preset-uuid", self.tmp / "out.wav"))
        self.assertEqual(form_field(api.requests[0]["body"], "preset"), "my-preset-uuid")
        self.assertIsNone(form_field(api.requests[0]["body"], "denoise"))

    def test_without_a_key_it_says_what_to_do_and_sends_nothing(self):
        with AuphonicApi() as api, mock.patch.object(auphonic, "BASE", api.url), mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(auphonic.ServiceError) as caught:
                auphonic.process(self.audio, "x", self.tmp / "out.wav")
        text = str(caught.exception)
        self.assertIn("AUPHONIC_API_KEY", text)
        self.assertIn(".env", text)
        self.assertEqual(api.requests, [])

    def test_a_refused_key_is_named_but_never_shown(self):
        with AuphonicApi(status=401) as api:
            with self.assertRaises(auphonic.ServiceError) as caught:
                self.run_with(api, lambda: auphonic.process(self.audio, "x", self.tmp / "out.wav"))
        text = str(caught.exception)
        self.assertIn("401", text)
        self.assertIn("ключ", text)
        self.assertNotIn(SECRET, text)
        self.assertFalse((self.tmp / "out.wav").exists())

    def test_a_failed_production_stops_with_its_reason(self):
        with AuphonicApi(final=2, error="Audio file too short") as api:
            with self.assertRaises(auphonic.ServiceError) as caught:
                self.run_with(api, lambda: auphonic.process(self.audio, "x", self.tmp / "out.wav"))
        self.assertIn("Audio file too short", str(caught.exception))
        self.assertFalse((self.tmp / "out.wav").exists())


class CheckKey(Case):
    def test_a_trial_request_says_the_key_works_without_showing_it(self):
        with AuphonicApi() as api:
            text = self.run_with(api, auphonic.check_key)
        self.assertIn("принят", text)
        self.assertNotIn(SECRET, text)
        self.assertEqual(api.requests[0]["path"], "/api/user.json")

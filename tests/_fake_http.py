"""A tiny HTTP server on 127.0.0.1 that plays a speech-to-text API. No traffic leaves the machine."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeApi:
    def __init__(self, status=200, payload=None):
        self.status, self.payload, self.requests = status, payload or {}, []
        api = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length)
                api.requests.append({"path": self.path, "headers": self.headers, "body": body})
                data = json.dumps(api.payload, ensure_ascii=False).encode("utf-8")
                self.send_response(api.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

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


def form_field(body: bytes, name: str):
    """Value of a simple multipart text field, or None."""
    marker = 'name="{}"\r\n\r\n'.format(name).encode()
    if marker not in body:
        return None
    return body.split(marker, 1)[1].split(b"\r\n", 1)[0].decode("utf-8")

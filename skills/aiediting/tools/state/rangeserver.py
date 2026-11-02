"""The workshop's static server: the stdlib one plus byte ranges, without which a <video> cannot seek.

Run as a script, so stdlib only. A range that is not one plain `bytes=` span gets the whole file, as the
HTTP spec allows; a conditional request is left to the stdlib, which knows how to answer 304.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

SPAN = re.compile(r"bytes=([0-9]{0,18})-([0-9]{0,18})")


def parse_range(header: str, size: int):
    """(first, last) of the file, None to send it whole, or () when the span lies past the end."""
    m = SPAN.fullmatch(header.strip())
    if not m or not (m.group(1) or m.group(2)):
        return None
    first, last = m.group(1), m.group(2)
    if not first:
        return (max(0, size - int(last)), size - 1) if int(last) and size else ()
    first = int(first)
    if last and int(last) < first:
        return None
    if first >= size:
        return ()
    return first, min(int(last), size - 1) if last else size - 1


class Part:
    """The file object for copyfile: reads only the span that was asked for."""

    def __init__(self, f, first: int, last: int):
        f.seek(first)
        self.f, self.left = f, last - first + 1

    def read(self, n: int = -1) -> bytes:
        data = self.f.read(self.left if n < 0 else min(n, self.left))
        self.left -= len(data)
        return data

    def close(self) -> None:
        self.f.close()


class Handler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def send_head(self):
        path = self.translate_path(self.path)
        wanted = self.headers.get("Range")
        if (self.command != "GET" or not wanted or "If-Modified-Since" in self.headers
                or path.endswith("/") or not os.path.isfile(path)):
            return super().send_head()
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        try:
            return self.send_part(f, wanted)
        except Exception:
            f.close()
            raise

    def send_part(self, f, wanted: str):
        stat = os.fstat(f.fileno())
        stamp = self.date_time_string(stat.st_mtime)
        if self.headers.get("If-Range", stamp) != stamp:
            span = None      # the file changed since the browser's copy: its part would not fit
        else:
            span = parse_range(wanted, stat.st_size)
        if span is None:
            f.close()
            return super().send_head()
        if not span:
            f.close()
            self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self.send_header("Content-Range", "bytes */%d" % stat.st_size)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        self.send_response(HTTPStatus.PARTIAL_CONTENT)
        self.send_header("Content-Type", self.guess_type(f.name))
        self.send_header("Content-Range", "bytes %d-%d/%d" % (*span, stat.st_size))
        self.send_header("Content-Length", str(span[1] - span[0] + 1))
        self.send_header("Last-Modified", stamp)
        self.end_headers()
        return Part(f, *span)


class Server(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        if not isinstance(sys.exc_info()[1], ConnectionError):      # a seek drops the previous request: routine
            super().handle_error(request, client_address)


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("port", type=int)
    args.add_argument("--bind", default="127.0.0.1")
    args.add_argument("--directory", required=True)
    opt = args.parse_args()
    with Server((opt.bind, opt.port), partial(Handler, directory=opt.directory)) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()

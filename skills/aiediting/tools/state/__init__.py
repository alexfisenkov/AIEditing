"""The workshop dashboard: state.js, a page with a snapshot inside, a server on 127.0.0.1.

Parts of it are adapted from AISpa (MIT); the notices are kept in NOTICE.md beside this file.
"""
from .server import serve, stop
from .snapshot import install_page, write_snapshot
from .stages import ORDER, WORDS, ask, close_wait, fresh, set_stage
from .store import log, now, read, rel, save

__all__ = ["ORDER", "WORDS", "ask", "close_wait", "fresh", "install_page", "log", "now", "read", "rel",
           "save", "serve", "set_stage", "stop", "write_snapshot"]

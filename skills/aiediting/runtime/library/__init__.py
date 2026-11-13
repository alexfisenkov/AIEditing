"""The person's library: one per computer, shared by all their editing skills.

Files about them, an inventory of their photos and footage, their own rules and what never to show.
Callers use the modules: `paths`, `inventory`, `rules`, `search`, `cli`.
"""
from .paths import LibraryError, find_library, set_library

__all__ = ["LibraryError", "find_library", "set_library"]

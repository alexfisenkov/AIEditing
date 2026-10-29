"""Passing a filter graph to ffmpeg without hitting the Windows command-line limit."""
from __future__ import annotations

import functools
from pathlib import Path
from typing import List

from .ffmpeg import run

INLINE_LIMIT = 6000  # characters; Windows caps a whole command line at 32767


@functools.lru_cache(maxsize=1)
def _file_option() -> str:
    """`-/filter_complex` (ffmpeg 7+) or the older `-filter_complex_script`."""
    help_text = run(["-h", "full"], check=False).stdout
    for line in help_text.splitlines():
        if line.lstrip().startswith("-filter_complex_script") and "deprecated" not in line:
            return "-filter_complex_script"
    return "-/filter_complex"


def graph_args(graph: str, tmpdir: Path) -> List[str]:
    """Arguments that hand `graph` to ffmpeg: inline when short, from a file when long."""
    if len(graph) <= INLINE_LIMIT:
        return ["-filter_complex", graph]
    path = Path(tmpdir) / "graph.txt"
    path.write_text(graph, encoding="utf-8")
    return [_file_option(), str(path)]

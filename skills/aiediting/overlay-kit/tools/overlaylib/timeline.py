"""`timeline`: the finished video with graphics as one picture, the sound in three stems under it, chapter markers.

The stems are audio renders of the same composition with the input prop `stem` (speech, sfx, music; src/kit/Sound.tsx
plays only that part), WAV in `таймлиния/` of the release folder. The file is FCPXML 1.10 for DaVinci Resolve, written by
AIEditing's own writer (runtime/media/fcpxml.py, loaded by path: the kit imports no package of the runtime).
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from . import remotion
from .common import FPS, FRAME_H, FRAME_W, KIT, ToolError, run, say, work_dir

FOLDER = "таймлиния"
NOTE = "таймлиния.md"
REPORT = "отчёт.md"
STEMS = [("speech", "голос", "Голос", "dialogue"), ("sfx", "звуки", "Звуки", "effects"), ("music", "музыка", "Музыка", "music")]
_CHAPTER = re.compile(r"^- (\d+):(\d\d):(\d\d(?:\.\d+)?) (.+)$")
_FINAL = (re.compile(r"^- Графика наложена: (.+)$"), re.compile(r"^- (.+) — готовый ролик с графикой$"))


def fcpxml():
    """The runtime's FCPXML writer next to this kit: in AIEditing and in a format skill alike."""
    for up in KIT.parents:
        path = up / "runtime" / "media" / "fcpxml.py"
        if path.is_file():
            spec = importlib.util.spec_from_file_location("aiediting_fcpxml", str(path))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ToolError("Рядом с набором нет runtime/media/fcpxml.py: таймлинию пишет набор внутри AIEditing или скилла формата.")


def _report(release: Path) -> List[str]:
    path = release / REPORT
    return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []


def final_video(release: Path, name: Optional[str]) -> Path:
    """The video `final` released: named, or the one the report names."""
    if not name:
        for line in _report(release):
            found = next((m for m in (r.match(line) for r in _FINAL) if m), None)
            if found:
                name = found.group(1).strip()
                break
    path = release / name if name else None
    if path is None or not path.is_file():
        raise ToolError("Не нашёл готовый ролик с графикой в {}: сначала overlay.py final, или назовите его --video".format(release))
    return path


def chapters(release: Path) -> List[Dict]:
    """Chapter markers from the «Главы» section of the release's report (seconds of the video given to prepare)."""
    out, inside = [], False
    for line in _report(release):
        if line.startswith("## "):
            inside = line.strip() == "## Главы"
            continue
        found = _CHAPTER.match(line) if inside else None
        if found:
            h, m, s, title = found.groups()
            out.append({"t": int(h) * 3600 + int(m) * 60 + float(s), "text": title.strip(), "kind": "chapter"})
    return out


def has_music(work: Path) -> bool:
    try:
        return bool(json.loads((work / "src" / "data" / "sfx.json").read_text(encoding="utf-8")).get("music"))
    except (OSError, ValueError):
        return False


def render_stem(work: Path, stem: str, out: Path) -> None:
    """One part of the sound of the whole composition, as WAV (an audio-only render of Remotion)."""
    props = work / "out" / "stem-{}.json".format(stem)
    props.parent.mkdir(parents=True, exist_ok=True)
    props.write_text(json.dumps({"stem": stem}), encoding="utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + ".part" + out.suffix)
    run([remotion._npx(), "remotion", "render", "src/index.ts", "Full", str(tmp), "--codec=wav", "--props={}".format(props),
         "--log=error", "--timeout=120000", *remotion._browser_args()], "Звук «{}»".format(stem), cwd=work, capture=False)
    tmp.replace(out)


def run_timeline(args) -> int:
    work, release = work_dir(args.work), Path(args.release).expanduser().resolve()
    video = final_video(release, getattr(args, "video", None))
    writer = fcpxml()
    remotion.ready(work)
    length = remotion.duration(work)
    audio = []
    for stem, file, name, role in STEMS:
        if stem == "music" and not has_music(work):
            continue
        out = release / FOLDER / "{}.wav".format(file)
        render_stem(work, stem, out)
        audio.append({"name": name, "role": role, "clips": [{"file": str(out), "start": 0.0, "in": 0.0, "dur": length}]})
    spec = {"name": video.stem, "fps": FPS, "width": FRAME_W, "height": FRAME_H, "duration": length,
            "video": [{"name": "Картинка", "clips": [{"file": str(video), "start": 0.0, "in": 0.0, "dur": length, "muted": True}]}],
            "audio": audio, "markers": chapters(release)}
    path = writer.write(spec, release / (video.stem + ".fcpxml"))
    writer.write_note(spec, path, release / NOTE, video.name, [
        "Картинка — готовый ролик с графикой, без звука; звук — дорожки «Голос», «Звуки» и «Музыка» под ним (WAV в папке "
        "«{}») с громкостью как в сцене, до выравнивания громкости готового ролика.".format(FOLDER)])
    say("Таймлиния: {}\nПамятка: {}".format(path, release / NOTE))
    return 0

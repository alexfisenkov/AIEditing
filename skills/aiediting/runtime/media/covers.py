"""Covers: a real frame of the video, 2–4 words in the format's design over a darkened side, 3840×2160 JPG.

The lower right corner is never drawn on (YouTube puts the length there); no blur, no 3D letters; each cover also gets
a 320 px preview, the size it is judged at. The words come from the person or the agent, never from here.
Settings come from `video.cover` of tokens.json when the design has it: font, weight, fg, shade, shade_alpha, size.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from ..render.design import load_design
from ..render.errors import RenderError, need

W, H = 3840, 2160
PREVIEW = (320, 180)
LAYOUTS = ("left", "top", "bottom")
SIDE, TEXT_W, SHADE_TO = 0.06, 0.56, 0.64   # shares of the width: margin, widest text, where the side shade ends
NAME = re.compile(r"^обложка-(\d+)\.jpg$")
DEFAULT = {"font": "display", "weight": "Bold", "fg": "white", "shade": "night", "shade_alpha": 0.82, "size": 0.15}
FEW, APART = 6, 2.0   # fewer frames from the pauses than this: more come from the video, this many seconds apart


def _rgb(d: Dict, name: str, fallback: str):
    value = d.get("color", {}).get(name, name)
    value = value if isinstance(value, str) and re.match(r"^#[0-9A-Fa-f]{6}$", value) else fallback
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def _frame(path: Path):
    image = need("PIL.Image")
    with image.open(str(path)) as im:
        im = im.convert("RGB")
        w, h = im.size
        if w * 9 > h * 16:
            cut = (w - h * 16 // 9) // 2
            im = im.crop((cut, 0, cut + h * 16 // 9, h))
        elif w * 9 < h * 16:
            cut = (h - w * 9 // 16) // 2
            im = im.crop((0, cut, w, cut + w * 9 // 16))
        return im.resize((W, H), image.LANCZOS)


def _shade(im, layout: str, rgb, alpha: float):
    image = need("PIL.Image")
    across = layout != "top"
    ramp = image.new("L", (256, 1) if across else (1, 256))
    stop = SHADE_TO if across else 0.6
    ramp.putdata([int(255 * alpha * max(0.0, 1 - (k / 255.0) / stop) ** 1.4) for k in range(256)])
    mask = ramp.resize((W, H), image.BILINEAR)
    return image.composite(image.new("RGB", (W, H), rgb), im, mask)


def _lines(font, words: List[str], room: int) -> List[str]:
    lines: List[str] = []
    for word in words:
        if lines and font.getlength(lines[-1] + " " + word) <= room:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def _fit(d: Dict, s: Dict, text: str):
    from ..render.fonts import font

    words, size = text.split(), int(float(s["size"]) * H)
    while True:
        f = font(d, s["font"], s["weight"], size)
        lines = _lines(f, words, int(TEXT_W * W))
        widest = max(f.getlength(line) for line in lines)
        if (len(lines) <= 3 and widest <= TEXT_W * W) or size <= 0.04 * H:
            return f, lines, int(size * 1.08)
        size = int(size * 0.92)


def _draw(im, d: Dict, s: Dict, text: str, layout: str):
    draw = need("PIL.ImageDraw")
    f, lines, step = _fit(d, s, text)
    block = step * len(lines)
    top = {"top": int(0.08 * H), "left": int((H - block) / 2 - 0.04 * H), "bottom": int(0.86 * H - block)}[layout]
    pen = draw.Draw(im)
    for k, line in enumerate(lines):
        pen.text((int(SIDE * W), top + k * step), line, font=f, fill=_rgb(d, s["fg"], "#FFFFFF"))
    return im


def next_number(out_dir: Path) -> int:
    found = [int(m.group(1)) for m in (NAME.match(p.name) for p in Path(out_dir).glob("обложка-*.jpg")) if m]
    return max(found, default=0) + 1


def clear(out_dir: Path) -> None:
    """Covers of an earlier text go before a new set is made (only the files this module writes)."""
    for folder in (Path(out_dir), Path(out_dir) / "превью"):
        for p in folder.glob("обложка-*.jpg"):
            if NAME.match(p.name):
                p.unlink()


def _save(im, path: Path, quality: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    im.save(str(tmp), format="JPEG", quality=quality)
    os.replace(str(tmp), str(path))
    return path


def render(frames: Sequence[Path], text: str, design, out_dir: Path, n: int = 6, first: int = 1) -> List[Path]:
    """`n` covers numbered from `first` (`обложка-07.jpg`…): frame and layout change from one to the next."""
    image = need("PIL.Image")
    frames, text = [Path(f) for f in frames], " ".join(str(text or "").split())
    if not frames:
        raise ValueError("Нет кадров для обложек: сначала шаг publish_pack (папка обложки/кадры)")
    if not text:
        raise ValueError("Нет слов для обложки: передайте --text \"2–4 слова\"")
    d = load_design(design)
    s = dict(DEFAULT, **(d.get("video", {}).get("cover") or {}))
    made = []
    for k in range(first - 1, first - 1 + n):
        layout = LAYOUTS[(k + k // len(frames)) % len(LAYOUTS)]
        im = _shade(_frame(frames[k % len(frames)]), layout, _rgb(d, s["shade"], "#0E0E10"), float(s["shade_alpha"]))
        im = _draw(im, d, s, text, layout)
        path = _save(im, Path(out_dir) / "обложка-{:02d}.jpg".format(k + 1), 92)
        _save(im.resize(PREVIEW, image.LANCZOS), Path(out_dir) / "превью" / path.name, 88)
        made.append(path)
    return made


def sheet(covers: Sequence[Path], out: Path, columns: int = 3) -> Path:
    """The previews side by side, numbered: what the person chooses from."""
    image, draw = need("PIL.Image"), need("PIL.ImageDraw")
    covers = [Path(c) for c in covers]
    rows, pad, label = (len(covers) + columns - 1) // columns, 12, 30
    canvas = image.new("RGB", (columns * (PREVIEW[0] + pad) + pad, rows * (PREVIEW[1] + label + pad) + pad), (14, 14, 16))
    pen = draw.Draw(canvas)
    for k, c in enumerate(covers):
        small = c.parent / "превью" / c.name
        with image.open(str(small if small.is_file() else c)) as im:
            tile = im.convert("RGB").resize(PREVIEW, image.LANCZOS)
        x, y = pad + k % columns * (PREVIEW[0] + pad), pad + k // columns * (PREVIEW[1] + label + pad)
        canvas.paste(tile, (x, y + label))
        pen.text((x, y + 8), c.stem.replace("обложка-", ""), fill=(236, 237, 239))
    return _save(canvas, Path(out), 90)


def sharpness(path: Path) -> float:
    """How much fine detail a frame holds: a blurred or moving face scores low."""
    image, stat, filt = need("PIL.Image"), need("PIL.ImageStat"), need("PIL.ImageFilter")
    with image.open(str(path)) as im:
        small = im.convert("L").resize((640, 360))
    return float(stat.Stat(small.filter(filt.FIND_EDGES)).var[0])


def order(frames: Sequence[Path]) -> List[Path]:
    """The sharpest frames first; the same frames always come in the same order, so `--more` goes on from there."""
    return sorted((Path(f) for f in frames), key=lambda f: (-round(sharpness(f), 3), f.name))


def grab(video: Path, moments: Sequence[float], folder: Path) -> List[Tuple[Path, float]]:
    """Frames of `video` at `moments` as `кадр-NN.jpg` in `folder` (the frames there before go): [(file, second)]."""
    from .ffmpeg import MediaError, run

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("кадр-*.jpg"):
        old.unlink()
    out = []
    for t in moments:
        path = folder / "кадр-{:02d}.jpg".format(len(out) + 1)
        try:
            run(["-ss", "{:.3f}".format(t), "-i", video, "-frames:v", "1", "-q:v", "2", path])
        except MediaError:
            continue
        if path.is_file():
            out.append((path, float(t)))
    return out


def _score(path: Path) -> float:
    try:
        return sharpness(path)
    except RenderError:  # no Pillow: every frame is as good, the middle of the window wins
        return 0.0


def more_moments(video: Path, taken: Sequence[float], duration: float, windows: int = 12) -> List[float]:
    """When the pauses of the speech gave fewer than FEW frames: in each window of the video without a taken moment,
    the sharpest of a few frames, never closer than APART s to another moment."""
    import tempfile

    chosen, step = [float(t) for t in taken], float(duration) / windows
    added: List[float] = []
    with tempfile.TemporaryDirectory(prefix="aiediting-") as tmp:
        for k in range(windows):
            lo, hi = k * step, (k + 1) * step
            if any(lo <= t < hi for t in chosen):
                continue
            tries = [lo + step * f for f in (0.5, 0.25, 0.75)]
            tries = [t for t in tries if 0.05 <= t <= duration - 0.1 and all(abs(t - c) >= APART for c in chosen)]
            got = grab(video, tries, Path(tmp) / str(k))
            if got:
                best = max(got, key=lambda g: _score(g[0]))[1]  # max keeps the first of equals: the middle
                chosen.append(best)
                added.append(round(best, 1))
    return sorted(added)

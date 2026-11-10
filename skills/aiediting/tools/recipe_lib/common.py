"""Local recipe I/O, bounded decoding and staged, no-clobber output placement."""
from __future__ import annotations

import contextlib
import errno
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class RecipeError(RuntimeError):
    """A concrete input, tool or output failure that is safe to show to the caller."""


def require_input(path) -> Path:
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise RecipeError("Input file does not exist: {}".format(path))
    return path


def probe(path) -> dict:
    from runtime.media import probe as passport
    return passport(require_input(path))


def ffmpeg(args, what="ffmpeg", check=True, cwd=None):
    from aelib.checks import argv_of
    if what not in {"ffmpeg", "ffprobe"}:
        raise RecipeError("Expected ffmpeg or ffprobe")
    base = [argv_of([what])[0], "-hide_banner"]
    if what == "ffmpeg":
        base += ["-nostdin", "-y"]
    done = subprocess.run(base + [str(a) for a in args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=cwd)
    if check and done.returncode:
        raise RecipeError("{} failed ({}): {}".format(what, done.returncode,
                          "\n".join(done.stderr.splitlines()[-8:])))
    return done


@contextlib.contextmanager
def output_file(output, replace=False, sources=()):
    given = Path(output).expanduser()
    if given.is_symlink():
        raise RecipeError("Choose a new output file, not a symlink")
    final = given.resolve()
    for source in sources:
        source = require_input(source)
        if final == source or (final.exists() and os.path.samefile(final, source)):
            raise RecipeError("Output must not replace a source file or its alias")
    if final.exists() and not replace:
        raise FileExistsError("Output exists; choose another path or use --replace: {}".format(final))
    final.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".aiediting-recipe-", dir=str(final.parent)) as work:
        staged = Path(work) / ("result" + final.suffix)
        yield staged
        if not staged.is_file() or staged.stat().st_size == 0:
            raise RecipeError("Recipe did not produce a non-empty artifact")
        if replace:
            os.replace(staged, final)
        else:
            # Atomic no-clobber publication, including two simultaneous recipes.
            try:
                os.link(staged, final)
            except OSError as exc:
                unsupported = {errno.EPERM, errno.EACCES, errno.EXDEV, errno.EINVAL, errno.ENOSYS,
                               getattr(errno, "ENOTSUP", errno.EINVAL), getattr(errno, "EOPNOTSUPP", errno.EINVAL)}
                if exc.errno not in unsupported:
                    raise
                # Volumes without hard links use an exclusive final-name reservation.
                # This copy is not atomic: use the artifact only after command success.
                created = None
                try:
                    with final.open("xb") as destination:
                        created = os.fstat(destination.fileno())
                        with staged.open("rb") as source:
                            shutil.copyfileobj(source, destination, length=1024 * 1024)
                        destination.flush()
                        os.fsync(destination.fileno())
                except BaseException:
                    if created is not None:
                        with contextlib.suppress(OSError):
                            current = os.lstat(final)
                            if (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino):
                                final.unlink()
                    raise


def write_json(path, data, replace=False) -> Path:
    path = Path(path).expanduser()
    if path.suffix.lower() != ".json":
        raise RecipeError("A JSON report needs a .json output path")
    with output_file(path, replace=replace) as staged:
        staged.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return path.resolve()


def extract_mono_audio(path, start_seconds, duration_seconds, sample_rate=8000):
    import numpy as np
    from aelib.checks import argv_of
    path = require_input(path)
    start, duration = float(start_seconds), float(duration_seconds)
    if not math.isfinite(start) or not math.isfinite(duration) or start < 0 or not 0 < duration <= 600:
        raise RecipeError("Use a finite audio window: start >= 0 and duration in (0, 600] seconds")
    if not isinstance(sample_rate, int) or not 1000 <= sample_rate <= 48000:
        raise RecipeError("sample_rate must be an integer from 1000 to 48000")
    if not probe(path)["has_audio"]:
        raise RecipeError("Input has no audio stream")
    args = [argv_of(["ffmpeg"])[0], "-hide_banner", "-nostdin", "-v", "error", "-ss", str(start),
            "-i", str(path), "-t", str(duration), "-vn", "-sn", "-dn", "-ac", "1", "-ar", str(sample_rate),
            "-f", "f32le", "pipe:1"]
    done = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if done.returncode:
        raise RecipeError("Audio decode failed: " + done.stderr.decode("utf-8", "replace")[-1200:])
    if not done.stdout or len(done.stdout) % 4:
        raise RecipeError("Audio window is empty or incomplete")
    audio = np.frombuffer(done.stdout, dtype="<f4").copy()
    if not np.isfinite(audio).all():
        raise RecipeError("Audio contains non-finite samples")
    return audio

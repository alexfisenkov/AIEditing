"""Finite optional local editing toolkit: inventory, checks, and one-off image cutout.

This module does not install packages or download models. The normal doctor/setup installer owns that.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .checks import status
from .paths import venv_python

MANIFEST = Path(__file__).resolve().parents[2] / "catalog" / "extra-tools.json"


class ToolboxError(RuntimeError):
    pass


def rows() -> list:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    listed = data["tools"]
    ids = [item["id"] for item in listed]
    if len(set(ids)) != len(ids):
        raise ToolboxError("В extra-tools.json повторяется id инструмента")
    return listed


def catalog() -> dict:
    return {row["id"]: row for row in rows()}


def installed() -> list:
    return [dict(id=row["id"], pin=row["pin"], what=row["what"], status=status(row)) for row in rows()]


def image_cutout(source, output) -> Path:
    """Remove a general object's image background with the explicit MIT BiRefNet Lite model.

    The private AIEditing Python runs rembg. Nothing is uploaded; the model must already be pinned
    and installed by doctor, so rembg cannot silently fetch its non-commercial default model.
    """
    source, output = Path(source).expanduser().resolve(), Path(output).expanduser().resolve()
    if not source.is_file():
        raise ToolboxError("Исходное изображение не найдено: {}".format(source))
    if source == output:
        raise ToolboxError("Исходник и результат должны быть разными файлами")
    if output.suffix.lower() != ".png":
        raise ToolboxError("Результат с прозрачностью должен иметь расширение .png")
    model_row = catalog()["birefnet-lite-model"]
    if not status(model_row)["ok"]:
        raise ToolboxError("Нужна проверенная локальная модель BiRefNet Lite; запустите doctor --install birefnet-lite-model --yes")
    python = venv_python()
    if not python.is_file():
        raise ToolboxError("Нет Python-окружения AIEditing: {}".format(python))
    code = """
import io
import sys
from pathlib import Path

import pooch
from PIL import Image
from rembg import new_session, remove

def no_download(*args, **kwargs):
    raise RuntimeError("Model download disabled: install the pinned model with ae.py doctor")

pooch.retrieve = no_download
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
data = remove(src.read_bytes(), session=new_session("birefnet-general-lite"))
image = Image.open(io.BytesIO(data))
if image.mode not in ("RGBA", "LA"):
    raise RuntimeError("Model did not return an alpha image")
image.save(dst, format="PNG")
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, staged_name = tempfile.mkstemp(prefix=".aiediting-cutout-", suffix=".png", dir=str(output.parent))
    os.close(fd)
    staged = Path(staged_name)
    try:
        env = dict(os.environ)
        env["REMBG_HOME"] = str(Path.home() / ".rembg")
        env.pop("U2NET_HOME", None)
        env.pop("MODEL_CHECKSUM_DISABLED", None)
        proc = subprocess.run([str(python), "-c", code, str(source), str(staged)], capture_output=True,
                              text=True, encoding="utf-8", errors="replace", env=env)
        if proc.returncode != 0 or staged.stat().st_size < 32:
            raise ToolboxError("BiRefNet не обработала изображение (код {}): {}".format(
                proc.returncode, "\n".join(proc.stderr.strip().splitlines()[-4:])))
        os.replace(str(staged), str(output))
    finally:
        staged.unlink(missing_ok=True)
    return output


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Дополнительные локальные инструменты AIEditing")
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="показать зафиксированные инструменты")
    listing.add_argument("--json", action="store_true")
    checking = sub.add_parser("check", help="проверить доступность без установки")
    checking.add_argument("--json", action="store_true")
    cutting = sub.add_parser("image-cutout", help="удалить фон на изображении через BiRefNet Lite")
    cutting.add_argument("source")
    cutting.add_argument("output")
    args = parser.parse_args(argv)
    try:
        if args.command == "image-cutout":
            print(image_cutout(args.source, args.output))
            return 0
        data = rows() if args.command == "list" else installed()
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            for row in data:
                suffix = " — {}".format(row["status"]["note"]) if "status" in row else ""
                print("{} {}: {}{}".format(row["id"], row["pin"], row["what"], suffix))
    except ToolboxError as exc:
        parser.exit(2, "{}\n".format(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

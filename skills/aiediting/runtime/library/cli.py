"""`library …` — the same commands from the workshop (`ae.py library`) and a format skill (`run.py library`).

    where · set <папка> · status
    scan <вид> [папка…]            new files with their metadata (no folder: the ones scanned before)
    sheet <вид> [--n 36]           a numbered sheet of small frames of files waiting for a description
    describe <вид> <json-файл>     the agent's rows into the inventory
    find "<фраза>" [--year Y]      candidates for an insert; the never list is left out
    rule "<текст>" [--format F] [--video V]  ·  rules [--format F]  ·  forbid "<кто/что>"
    stock "<запрос>" [--provider P] [--take N]   free stock video by the person's key; --take puts hit N in the library
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from . import inventory, rules, search, stock
from .paths import KINDS, LAYOUT, LibraryError, find_library, need_library, pointer_file, set_library, wanted

SHEETS = "листы"


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="library")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("where")
    sub.add_parser("status")
    sub.add_parser("set").add_argument("path")
    p = sub.add_parser("scan")
    p.add_argument("kind")
    p.add_argument("roots", nargs="*")
    p = sub.add_parser("sheet")
    p.add_argument("kind")
    p.add_argument("--n", type=int, default=36)
    p.add_argument("--grid", type=int, default=6)
    p = sub.add_parser("describe")
    p.add_argument("kind")
    p.add_argument("file")
    p = sub.add_parser("find")
    p.add_argument("phrase")
    p.add_argument("--year", type=int)
    p.add_argument("--limit", type=int, default=5)
    p = sub.add_parser("rule")
    p.add_argument("text")
    p.add_argument("--format")
    p.add_argument("--video")
    sub.add_parser("rules").add_argument("--format")
    sub.add_parser("forbid").add_argument("what")
    p = sub.add_parser("stock")
    p.add_argument("query")
    p.add_argument("--provider", choices=sorted(stock.KEYS))
    p.add_argument("--take", type=int)
    return ap


def _where() -> str:
    found = find_library()
    if found is not None:
        return str(found)
    named = wanted()
    if named is not None:
        raise LibraryError("Библиотека записана в {}, но папки нет (диск не подключён?)".format(named))
    raise LibraryError("Библиотека не подключена: выберите папку командой library set <папка>")


def _status(lib: Path) -> str:
    lines = ["Библиотека: {}".format(lib)]
    for kind, row in inventory.summary(lib).items():
        lines.append("{}: описано {}, ждут описания {}{}".format(
            kind, row["described"], row["pending"], "; папки: " + ", ".join(row["roots"]) if row["roots"] else ""))
    lines.append("Правил: {}; в «чего нельзя»: {}".format(
        sum(1 for l in (lib / LAYOUT["rules"]).read_text(encoding="utf-8").splitlines() if l.startswith("- ")),
        len(rules.forbidden(lib))))
    return "\n".join(lines)


def _sheet(lib: Path, kind: str, n: int, grid: int) -> str:
    rows = inventory.pending(lib, kind)[:max(1, n)]
    if not rows:
        return "Все файлы вида «{}» описаны".format(kind)
    folder = lib / LAYOUT["inventory"] / SHEETS
    number = len(list(folder.glob("{}-*.jpg".format(kind)))) + 1 if folder.is_dir() else 1
    out = inventory.sheet([inventory.file_of(lib, r) for r in rows], folder / "{}-{:03d}.jpg".format(kind, number), grid)
    lines = ["Лист: {}".format(out)]
    for i, r in enumerate(rows, 1):
        lines.append("{}. {} · {} · {} · {} · {}".format(i, r["f"], r["type"], r["date"] or "дата ?",
                                                        r["orient"] or "?", "{} с".format(r["dur"]) if r["dur"] else "—"))
    return "\n".join(lines)


def _describe(lib: Path, kind: str, file: str) -> str:
    try:
        data = json.loads(Path(file).expanduser().read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LibraryError("Не читается файл описаний {}: {}".format(file, exc))
    rows = data.get("rows") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise LibraryError("В файле описаний нужен список строк (или {\"rows\": [...]})")
    done = inventory.describe(lib, kind, rows)
    return "Записано строк описи: {}; ждут описания: {}".format(done, len(inventory.pending(lib, kind)))


def _find(lib: Path, phrase: str, year, limit: int) -> str:
    found = search.candidates(inventory.load(lib), phrase, year, limit, rules.forbidden(lib))
    if not found:
        return "Под эту фразу в библиотеке ничего нет"
    return "\n".join("{} · {} · {}{}".format(r["score"], r["f"], r.get("what") or "—",
                                             " · " + ", ".join(r["who"]) if r.get("who") else "") for r in found)


def _stock(lib: Path, query: str, provider, take) -> str:
    """Hits of the first service with a key (or the named one); `take` puts one of them into the library."""
    hits, last = [], None
    for name in [provider] if provider else sorted(stock.KEYS):
        try:
            hits = stock.search(query, name)
        except stock.StockError as exc:
            last = exc
            continue
        if hits:
            break
    if not hits:
        raise last or stock.StockError("Под этот запрос в стоках ничего нет")
    if take:
        if not 1 <= take <= len(hits):
            raise LibraryError("Нет результата №{}: найдено {}".format(take, len(hits)))
        return "Сток в библиотеке: {}".format(stock.download(hits[take - 1], lib)["f"])
    return "\n".join("{}. {}×{} · {} с".format(i, h["width"], h["height"], h["dur"]) for i, h in enumerate(hits, 1))


def run(argv: List[str]) -> str:
    """The answer of one command; LibraryError (a ValueError) when it cannot be done."""
    opt = _parser().parse_args(argv)
    if opt.cmd == "where":
        return _where()
    if opt.cmd == "set":
        lib = set_library(Path(opt.path))
        return "Библиотека: {}\nУказатель: {}".format(lib, pointer_file())
    lib = need_library()
    if opt.cmd == "status":
        return _status(lib)
    if opt.cmd == "scan":
        rows = inventory.scan(lib, opt.kind, [Path(r) for r in opt.roots])
        head = ["Новых файлов ({}): {}".format(opt.kind, len(rows))]
        return "\n".join(head + [r["f"] for r in rows[:20]] + (["…"] if len(rows) > 20 else []))
    if opt.cmd == "sheet":
        return _sheet(lib, opt.kind, opt.n, opt.grid)
    if opt.cmd == "describe":
        return _describe(lib, opt.kind, opt.file)
    if opt.cmd == "find":
        return _find(lib, opt.phrase, opt.year, opt.limit)
    if opt.cmd == "rule":
        return "Записал в правила: {}".format(rules.add_rule(lib, opt.text, opt.format, opt.video))
    if opt.cmd == "rules":
        return rules.rules_text(lib, opt.format) or "Правил пока нет"
    if opt.cmd == "stock":
        return _stock(lib, opt.query, opt.provider, opt.take)
    return "Записал в «чего нельзя»: {}".format(rules.forbid(lib, opt.what))


def main(argv: List[str]) -> int:
    try:
        print(run(argv))
    except Exception as exc:  # a refusal is one line for the person, not a trace
        if not isinstance(exc, (LibraryError, OSError)) and type(exc).__name__ != "MediaError":
            raise
        print("ошибка: {}".format(exc))
        return 1
    return 0


__all__ = ["KINDS", "main", "run"]
